# documents/views.py

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
import json

from django.http import JsonResponse
from django.db.models import Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank

from documents.models import Document
from documents.utils import get_accessible_documents


from django.http import (
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import render, redirect
from django.db.models import Sum
from django.contrib.postgres.search import SearchVector

from .models import Document, Folder
from .utils.text_extractor import extract_text_from_file
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, F, Exists, OuterRef
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F
from django.contrib.postgres.search import SearchQuery, SearchRank

from documents.models import Document, Folder
from documents.utils import get_accessible_documents

from django.db.models import Q, Count, Sum, F
from django.contrib.postgres.search import SearchQuery, SearchRank

from django.http import (
    HttpResponseForbidden,
    FileResponse,
    JsonResponse,
)

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from .models import Document, Folder


# =====================================================
# CONSTANTS / LIMITS
# =====================================================

MAX_PREMIUM_UPLOAD_MB = 50
MAX_PREMIUM_UPLOAD_BYTES = MAX_PREMIUM_UPLOAD_MB * 1024 * 1024

MAX_PREMIUM_STORAGE_MB = 500
MAX_PREMIUM_STORAGE_BYTES = MAX_PREMIUM_STORAGE_MB * 1024 * 1024


# =====================================================
# ROLE HELPERS
# =====================================================

def get_user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_staff:
        return "admin"
    if hasattr(user, "profile") and hasattr(user.profile, "role"):
        return user.profile.role
    return "basic"


def is_premium(user):
    return get_user_role(user) == "premium"


# =====================================================
# DOCUMENT LIST
# =====================================================


@login_required
def document_list(request):
    user = request.user
    role = getattr(getattr(user, "profile", None), "role", None)
    folder_id = request.GET.get("folder")
    query = request.GET.get("q", "").strip()

    # ==================================================
    # 📄 BASE QUERYSET — ACCESSIBLE DOCUMENTS
    # ==================================================
    if user.is_staff:
        documents_qs = Document.objects.all()
    else:
        documents_qs = get_accessible_documents(user)

    # ==================================================
    # 📁 FOLDER TREE — ONLY VISIBLE DOCUMENT FOLDERS
    # ==================================================
    if user.is_staff:
        folders = Folder.objects.all()
    else:
        visible_folder_ids = (
            documents_qs
            .exclude(folder__isnull=True)
            .values_list("folder_id", flat=True)
            .distinct()
        )

        folders = (
            Folder.objects
            .filter(
                Q(id__in=visible_folder_ids) |
                Q(children__id__in=visible_folder_ids)
            )
            .distinct()
        )

    # ==================================================
    # 📁 FOLDER FILTER
    # ==================================================
    if folder_id:
        documents_qs = documents_qs.filter(folder_id=folder_id)

    # ==================================================
    # 🔍 SEARCH (VECTOR + FALLBACK)
    # ==================================================
    if query:
        search_query = SearchQuery(query, config="english")

        documents_qs = (
            documents_qs
            .annotate(rank=SearchRank(F("search_vector"), search_query))
            .filter(
                Q(rank__gte=0.1) |
                Q(file__icontains=query) |
                Q(title__icontains=query)
            )
            .order_by("-rank", "-created_at")
            .distinct()
        )
    else:
        documents_qs = documents_qs.order_by("-created_at")

    # ==================================================
    # ✅ RESPONSE
    # ==================================================
    return render(request, "documents/list.html", {
        "documents": documents_qs,
        "folders": folders,
        "active_folder": folder_id,
        "query": query,
    })



# =====================================================
# DOCUMENT UPLOAD
# =====================================================

# constants assumed to already exist
# MAX_PREMIUM_UPLOAD_BYTES
# MAX_PREMIUM_STORAGE_BYTES




# Limits (already defined in your settings or constants)
# MAX_PREMIUM_UPLOAD_BYTES
# MAX_PREMIUM_STORAGE_BYTES


from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.db.models import Sum
from django.contrib.postgres.search import SearchVector

from accounts.models import OrganizationMember
from documents.models import Document, Folder
from documents.utils import extract_text_from_file
from documents.constants import (
    MAX_PREMIUM_UPLOAD_BYTES,
    MAX_PREMIUM_STORAGE_BYTES,
)


@login_required
def document_upload(request):
    user = request.user
    profile = getattr(user, "profile", None)
    legacy_role = getattr(profile, "role", None)

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # =========================
    # 🏢 ORGANIZATION CONTEXT
    # =========================
    member = (
        OrganizationMember.objects
        .select_related("organization")
        .filter(user=user)
        .first()
    )

    is_org_admin = member and member.role == "admin"
    is_org_premium_user = member and member.role == "member" and member.tier == "premium"

    # =========================
    # 🔐 LEGACY ROLE SANITY
    # =========================
    if user.is_staff and legacy_role == "premium":
        profile.role = "admin"
        profile.save(update_fields=["role"])
        legacy_role = "admin"

    # =========================
    # 🔐 UPLOAD PERMISSION GATE
    # =========================
    allowed = (
        user.is_staff
        or is_org_admin
        or is_org_premium_user
        or legacy_role == "premium"
    )

    if not allowed:
        if is_ajax:
            return JsonResponse({"error": "Not allowed"}, status=403)
        return HttpResponseForbidden("Not allowed")

    # =========================
    # 📤 POST — UPLOAD FILES
    # =========================
    if request.method == "POST":
        files = request.FILES.getlist("files")
        folder_id = request.POST.get("folder")

        folder = Folder.objects.filter(id=folder_id, owner=user).first() if folder_id else None

        if not files:
            msg = "No files selected."
            if is_ajax:
                return JsonResponse({"error": msg}, status=400)
            return render(request, "documents/upload.html", {
                "folders": Folder.objects.filter(owner=user),
                "error": msg,
            })

        # =========================
        # 🔐 DETERMINE OWNERSHIP
        # =========================
        """
        RULES:
        - Org admin  → company document
        - Org premium user → private personal document
        - Legacy premium user → private personal document
        """

        upload_as_company = is_org_admin
        upload_as_private = is_org_premium_user or legacy_role == "premium"

        # =========================
        # 📦 UPLOAD SIZE CHECK
        # =========================
        total_upload_size = sum(f.size for f in files)

        if upload_as_private and total_upload_size > MAX_PREMIUM_UPLOAD_BYTES:
            msg = "Upload exceeds your per-upload size limit."
            if is_ajax:
                return JsonResponse({"error": msg}, status=400)
            return render(request, "documents/upload.html", {
                "folders": Folder.objects.filter(owner=user),
                "error": msg,
            })

        # =========================
        # 💾 STORAGE QUOTA CHECK (PRIVATE ONLY)
        # =========================
        if upload_as_private:
            used_storage = (
                Document.objects
                .filter(owner=user)
                .aggregate(total=Sum("file_size"))["total"] or 0
            )

            if used_storage + total_upload_size > MAX_PREMIUM_STORAGE_BYTES:
                msg = "Storage quota exceeded."
                if is_ajax:
                    return JsonResponse({"error": msg}, status=400)
                return render(request, "documents/upload.html", {
                    "folders": Folder.objects.filter(owner=user),
                    "error": msg,
                })

        # =========================
        # 💾 SAVE FILES + INDEX
        # =========================
        uploaded_docs = []

        for f in files:
            if upload_as_company:
                document = Document.objects.create(
                    organization=member.organization,
                    file=f,
                    file_size=f.size,
                    is_public=False,
                    uploaded_by_admin=True,
                )
            else:
                document = Document.objects.create(
                    owner=user,
                    folder=folder,
                    file=f,
                    file_size=f.size,
                    is_public=False,
                    uploaded_by_admin=False,
                )

            try:
                extracted_text = extract_text_from_file(document.file.path) or ""
                document.extracted_text = extracted_text
                document.search_vector = SearchVector("extracted_text")
                document.save(update_fields=["extracted_text", "search_vector"])
            except Exception as e:
                print(f"❌ Text extraction failed for Document {document.id}: {e}")

            uploaded_docs.append(document.id)

        # =========================
        # ✅ RESPONSE
        # =========================
        if is_ajax:
            return JsonResponse({
                "success": True,
                "uploaded_count": len(uploaded_docs),
            })

        if upload_as_private:
            return redirect("my_documents")

        return redirect("document_list")

    # =========================
    # 📄 GET — UPLOAD FORM
    # =========================
    return render(request, "documents/upload.html", {
        "folders": Folder.objects.filter(owner=user),
    })


# =====================================================
# DOCUMENT PREVIEW / DOWNLOAD
# =====================================================

@login_required
def document_preview(request, document_id=None, doc_id=None):
    user = request.user

    # Resolve ID from either URL style
    resolved_id = document_id or doc_id

    document = get_object_or_404(Document, id=resolved_id)

    # =========================
    # 🔐 ACCESS RULES
    # =========================

    # Admin preview
    if user.is_staff and document.uploaded_by_admin:
        return render(request, "documents/document_preview.html", {
            "document": document
        })

    # Premium user preview
    if getattr(user.profile, "role", None) == "premium" and (
        document.owner == user or document.is_public
    ):
        return render(request, "documents/document_preview.html", {
            "document": document
        })

    # Public document
    if document.is_public:
        return render(request, "documents/document_preview.html", {
            "document": document
        })

    # Access denied
    return render(request, "documents/access_denied.html", status=403)



@login_required
def document_download(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if not (request.user.is_staff or document.owner == request.user or document.is_public):
        return HttpResponseForbidden("Not allowed")

    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1],
    )


# =====================================================
# DELETE / BULK DELETE
# =====================================================

@login_required
def document_delete(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if not (request.user.is_staff or document.owner == request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        document.file.delete(save=False)
        document.delete()
        return redirect("document_list")

    return render(request, "documents/confirm_delete.html", {"document": document})


@login_required
def bulk_delete_documents(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    user = request.user
    role = getattr(user.profile, "role", None)
    ids = request.POST.getlist("document_ids")

    if not ids:
        return redirect("document_list")

    if user.is_staff:
        Document.objects.filter(id__in=ids).delete()

    elif role == "premium":
        Document.objects.filter(id__in=ids, owner=user).delete()

    else:
        return HttpResponseForbidden("Not allowed")

    return redirect("document_list")


# =====================================================
# INLINE EDIT (AJAX)
# =====================================================

@staff_member_required
@require_POST
def document_inline_update(request, pk):
    document = get_object_or_404(Document, pk=pk)

    document.title = request.POST.get("title", "").strip()
    document.is_public = request.POST.get("is_public") == "true"

    folder_id = request.POST.get("folder")
    document.folder_id = folder_id if folder_id else None

    document.save()

    return JsonResponse({
        "success": True,
        "title": document.display_name,
    })


# =====================================================
# AJAX SEARCH
# =====================================================


@login_required
def ajax_document_search(request):
    user = request.user

    query = request.GET.get("q", "").strip()
    folder_id = request.GET.get("folder")

    # ==================================================
    # 📄 BASE QUERYSET — ACCESSIBLE DOCUMENTS ONLY
    # ==================================================
    if user.is_staff:
        qs = Document.objects.all()
    else:
        qs = get_accessible_documents(user)

    # ==================================================
    # 📁 FOLDER FILTER
    # ==================================================
    if folder_id:
        qs = qs.filter(folder_id=folder_id)

    # ==================================================
    # 🔍 SEARCH (VECTOR + FALLBACK)
    # ==================================================
    if query:
        search_query = SearchQuery(query, config="english")
        qs = (
            qs.annotate(rank=SearchRank(F("search_vector"), search_query))
            .filter(
                Q(rank__gte=0.1) |
                Q(file__icontains=query) |
                Q(title__icontains=query)
            )
            .order_by("-rank", "-created_at")
        )
    else:
        qs = qs.order_by("-created_at")

    # ==================================================
    # 🚦 LIMIT RESULTS
    # ==================================================
    qs = qs[:50]

    # ==================================================
    # 📦 RESPONSE PAYLOAD
    # ==================================================
    data = []
    for d in qs:
        data.append({
            "id": d.id,
            "title": d.display_name,
            "is_public": d.is_public,
            "owner": d.owner.username if d.owner else None,
            "organization": d.organization.name if d.organization else None,
            "can_edit": user.is_staff or d.owner == user,
        })

    return JsonResponse({"results": data})


@login_required
def toggle_public(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    # Only admins can toggle visibility
    if not request.user.is_staff:
        return HttpResponseForbidden("Not allowed")

    document.is_public = not document.is_public
    document.save(update_fields=["is_public"])

    return redirect("document_list")




@login_required
def create_folder(request):
    user = request.user
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", None)

    # =========================
    # 🔐 ACCESS CONTROL
    # =========================
    if not (user.is_staff or role == "premium"):
        return HttpResponseForbidden("Not allowed")

    if request.method != "POST":
        return redirect("document_list")

    name = request.POST.get("name", "").strip()
    parent_id = request.POST.get("parent")

    # =========================
    # ❌ VALIDATION
    # =========================
    if not name:
        messages.error(request, "Folder name is required.")
        return redirect("document_list")

    parent = None

    # =========================
    # 📁 PARENT RESOLUTION
    # =========================
    if parent_id:
        # Guard against empty / invalid values
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            messages.error(request, "Invalid parent folder.")
            return redirect("document_list")

        parent = get_object_or_404(Folder, id=parent_id)

        # Non-admins can only nest under their own folders
        if not user.is_staff and parent.owner != user:
            messages.error(request, "Invalid parent folder.")
            return redirect("document_list")

    # =========================
    # 📁 CREATE FOLDER
    # =========================
    folder = Folder(
        name=name,
        owner=user,
        parent=parent,
        is_public=False
    )

    try:
        folder.full_clean()  # model-level validation
        folder.save()
        messages.success(request, "Folder created successfully.")
    except ValidationError as e:
        messages.error(
            request,
            e.message_dict.get("__all__", ["Invalid folder structure."])[0]
        )

    return redirect("document_list")



@login_required
def delete_folder(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id)
    user = request.user

    # Only admin or folder owner can delete
    if not (user.is_staff or folder.owner == user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        # Optional: move docs out instead of deleting
        Document.objects.filter(folder=folder).delete()

        # Delete subfolders first
        folder.children.all().delete()

        folder.delete()

    return redirect("document_list")
@login_required
def rename_folder(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id)
    user = request.user

    # Only admin or folder owner can rename
    if not (user.is_staff or folder.owner == user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        new_name = request.POST.get("name", "").strip()
        if new_name:
            folder.name = new_name
            folder.save(update_fields=["name"])

    return redirect("document_list")



@login_required
@require_POST
def move_folder(request):
    user = request.user

    # =========================
    # SAFE JSON PARSE
    # =========================
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid request data"},
            status=400
        )

    folder_id = data.get("folder_id")
    new_parent_id = data.get("new_parent_id")

    if not folder_id:
        return JsonResponse(
            {"success": False, "error": "Folder ID required"},
            status=400
        )

    folder = get_object_or_404(Folder, id=folder_id)

    # =========================
    # PERMISSION CHECK
    # =========================
    role = getattr(getattr(user, "profile", None), "role", None)

    # Admin: can move anything
    # Premium: can move ONLY own folders
    if not user.is_staff:
        if role != "premium" or folder.owner != user:
            return JsonResponse(
                {"success": False, "error": "Not allowed"},
                status=403
            )

    # =========================
    # RESOLVE PARENT
    # =========================
    parent = None
    if new_parent_id:
        parent = get_object_or_404(Folder, id=new_parent_id)

        # Prevent moving into another user's folder
        if not user.is_staff and parent.owner != user:
            return JsonResponse(
                {"success": False, "error": "Invalid target folder"},
                status=403
            )

    # =========================
    # PREVENT SELF-PARENTING
    # =========================
    if parent and parent.id == folder.id:
        return JsonResponse(
            {"success": False, "error": "Invalid target"},
            status=400
        )

    # =========================
    # PREVENT CIRCULAR NESTING
    # =========================
    current = parent
    while current:
        if current == folder:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Cannot move folder into its own child"
                },
                status=400
            )
        current = current.parent

    # =========================
    # APPLY MOVE
    # =========================
    folder.parent = parent
    folder.save(update_fields=["parent"])

    return JsonResponse({"success": True})


@login_required
def document_detail(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if not (
        request.user.is_staff or
        document.owner == request.user or
        document.is_public
    ):
        return HttpResponseForbidden("Not allowed")

    return redirect("document_preview", doc_id=document.id)



@login_required
def my_documents(request):
    user = request.user
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", None)

    # =========================
    # 🔐 ACCESS CONTROL
    # =========================
    if not (user.is_staff or role == "premium"):
        return HttpResponseForbidden("Not allowed")

    # =========================
    # 🔍 SEARCH & FILTERS
    # =========================
    query = request.GET.get("q", "").strip()
    folder_id = request.GET.get("folder")

    # Base queryset: user's documents only
    documents = Document.objects.filter(owner=user)

    # =========================
    # 📂 FOLDER FILTER (TREE-AWARE)
    # =========================
    active_folder = None

    if folder_id:
        active_folder = Folder.objects.filter(
            id=folder_id,
            owner=user
        ).first()

        if active_folder:
            # Include documents in this folder AND its subfolders
            folder_ids = [active_folder.id]

            def collect_children(folder):
                for child in folder.children.all():
                    folder_ids.append(child.id)
                    collect_children(child)

            collect_children(active_folder)

            documents = documents.filter(folder_id__in=folder_ids)

    # =========================
    # 🔍 SEARCH (SAFE FALLBACK)
    # =========================
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(extracted_text__icontains=query) |
            Q(file__icontains=query)
        )

    documents = documents.order_by("-created_at")

    # =========================
    # 📁 FOLDER TREE (SIDEBAR)
    # =========================
    folders = (
        Folder.objects
        .filter(owner=user)
        .select_related("parent")
        .prefetch_related("children")
        .order_by("name")
    )

    return render(
        request,
        "documents/my_documents.html",
        {
            "documents": documents,
            "folders": folders,
            "active_folder": active_folder.id if active_folder else None,
            "query": query,
        }
    )



@login_required
def edit_document(request, document_id):
    doc = get_object_or_404(Document, id=document_id)

    # 🔐 Only owner or admin can edit
    if not (request.user.is_staff or doc.owner == request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        doc.title = request.POST.get("title", "").strip()
        doc.folder_id = request.POST.get("folder") or None
        doc.save()

        return redirect("my_documents")

    return render(request, "documents/edit_document.html", {
        "doc": doc,
        "folders": Folder.objects.filter(owner=request.user),
    })

@login_required
def delete_document(request, document_id):
    doc = get_object_or_404(Document, id=document_id)

    # 🔐 Owner or admin only
    if not (request.user.is_staff or doc.owner == request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        doc.file.delete(save=False)  # delete file from storage
        doc.delete()
        return redirect("my_documents")

    return render(request, "documents/confirm_delete.html", {
        "doc": doc
    })



@login_required
def document_versions(request, document_id):
    doc = get_object_or_404(Document, id=document_id)

    # 🔐 Owner or admin only
    if not (request.user.is_staff or doc.owner == request.user):
        return HttpResponseForbidden("Not allowed")

    versions = doc.versions.all().order_by("-created_at")

    return render(request, "documents/document_versions.html", {
        "doc": doc,
        "versions": versions,
    })




@login_required
def share_document(request, document_id):
    doc = get_object_or_404(Document, id=document_id)

    # 🔐 Only owner or admin can share
    if not (request.user.is_staff or doc.owner == request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        user_id = request.POST.get("user_id")

        if user_id:
            DocumentShare.objects.get_or_create(
                document=doc,
                user_id=user_id
            )

        return redirect("my_documents")

    users = User.objects.exclude(id=request.user.id)

    return render(request, "documents/share_document.html", {
        "doc": doc,
        "users": users,
    })




@login_required
@require_POST
def move_document(request):
    user = request.user
    role = getattr(getattr(user, "profile", None), "role", None)

    # =========================
    # PERMISSION CHECK
    # =========================
    if not (user.is_staff or role == "premium"):
        return JsonResponse(
            {"success": False, "error": "Not allowed"},
            status=403
        )

    # =========================
    # PARSE REQUEST DATA
    # Supports:
    # - JSON (drag & drop, multi-select)
    # - Form POST (legacy single move)
    # =========================
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
            document_ids = data.get("document_ids", [])
            folder_id = data.get("folder_id")
        else:
            # Legacy fallback
            doc_id = request.POST.get("doc_id")
            folder_id = request.POST.get("folder_id")
            document_ids = [doc_id] if doc_id else []
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid request"},
            status=400
        )

    if not document_ids:
        return JsonResponse(
            {"success": False, "error": "No documents specified"},
            status=400
        )

    # =========================
    # TARGET FOLDER (OPTIONAL)
    # =========================
    folder = None
    if folder_id:
        if user.is_staff:
            folder = get_object_or_404(Folder, id=folder_id)
        else:
            folder = get_object_or_404(Folder, id=folder_id, owner=user)

    # =========================
    # MOVE DOCUMENTS
    # =========================
    moved = 0

    documents = Document.objects.filter(id__in=document_ids)

    for doc in documents:
        # Admin can move any document
        if user.is_staff or doc.owner == user:
            doc.folder = folder
            doc.save(update_fields=["folder"])
            moved += 1

    return JsonResponse({
        "success": True,
        "moved": moved
    })
















