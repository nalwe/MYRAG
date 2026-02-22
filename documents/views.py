from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST

from documents.models import Document, Folder
from documents.utils import get_accessible_documents
from documents.utils.text_extractor import extract_text_from_file
from accounts.models import OrganizationMember
from rag.indexer import index_document

from rag.indexer import index_document  # 🔥 ADD THIS IMPORT

from rag.indexer import index_document
from documents.utils.text_extractor import extract_text_from_file
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from accounts.models import OrganizationMember
from documents.models import Document
from bs4 import BeautifulSoup
import os



# =========================
# 📄 DOCUMENT LIST
# =========================

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q
from django.contrib.auth.decorators import login_required


@login_required
def document_list(request):
    user = request.user
    folder_id = request.GET.get("folder")
    query = request.GET.get("q", "").strip()

    # =========================
    # BASE QUERYSET
    # =========================
    if user.is_superuser:
        documents = Document.objects.all()
        folders = Folder.objects.all()
    else:
        documents = get_accessible_documents(user)
        folders = Folder.objects.filter(uploaded_by=user)

    active_folder = None

    # =========================
    # FOLDER FILTER
    # =========================
    if folder_id:
        active_folder = folders.filter(id=folder_id).first()
        if active_folder:
            documents = documents.filter(folder_id=active_folder.id)

    # =========================
    # SEARCH (Scoped if folder selected)
    # =========================
    if query:
        search_query = SearchQuery(query, config="english")

        documents = (
            documents
            .annotate(rank=SearchRank("search_vector", search_query))
            .filter(
                Q(rank__gte=0.1) |
                Q(title__icontains=query) |
                Q(extracted_text__icontains=query)
            )
            .order_by("-rank", "-created_at")
            .distinct()
        )
    else:
        documents = documents.order_by("-created_at")

    # =========================
    # RAG RESTRICTION FLAG (Session)
    # =========================
    restrict_rag = request.session.get("restrict_rag", False)

    return render(
        request,
        "documents/list.html",
        {
            "documents": documents,
            "folders": folders,
            "active_folder": active_folder,
            "query": query,
            "restrict_rag": restrict_rag,
        }
    )



from django.views.decorators.http import require_POST
from django.http import JsonResponse

@login_required
@require_POST
def toggle_rag_restriction(request):
    value = request.POST.get("value") == "true"
    request.session["restrict_rag"] = value
    return JsonResponse({"success": True})


# =========================
# 📤 UPLOAD DOCUMENT
# =========================


@login_required
@require_http_methods(["GET", "POST"])
def document_upload(request):
    user = request.user
    MAX_SIZE = 15 * 1024 * 1024  # 15MB per file

    member = (
        OrganizationMember.objects
        .select_related("organization")
        .filter(user=user)
        .first()
    )

    if not (user.is_superuser or (member and member.is_admin())):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        files = request.FILES.getlist("files")
        folder_id = request.POST.get("folder")

        if not files:
            return JsonResponse(
                {"success": False, "error": "No files selected."},
                status=400,
            )

        # 🔒 BLOCK FILES OVER 15MB (BACKEND ENFORCEMENT)
        for f in files:
            if f.size > MAX_SIZE:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"{f.name} exceeds 15MB limit."
                    },
                    status=400,
                )

        # 📁 Resolve folder safely
        selected_folder = None
        if folder_id:
            try:
                selected_folder = Folder.objects.get(
                    id=folder_id,
                    uploaded_by=user
                )
            except Folder.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Invalid folder selected."},
                    status=400,
                )

        try:
            for f in files:

                # =========================
                # 💾 STEP 1: SAVE DOCUMENT
                # =========================
                doc = Document.objects.create(
                    uploaded_by=user,
                    organization=None if user.is_superuser else member.organization,
                    is_public=user.is_superuser,
                    file=f,
                    folder=selected_folder,
                )

                # =========================
                # 🔍 STEP 2: EXTRACT TEXT
                # =========================
                try:
                    extracted_text = extract_text_from_file(doc.file.path) or ""
                except Exception as e:
                    print(f"[EXTRACTION ERROR] {f.name}: {str(e)}")
                    extracted_text = ""

                doc.extracted_text = extracted_text
                doc.save(update_fields=["extracted_text"])

                # =========================
                # 🤖 STEP 3: INDEX FOR RAG
                # =========================
                if extracted_text.strip():
                    try:
                        index_document(doc)
                        print(f"[INDEXED] {doc.id} - {doc.file.name}")
                    except Exception as e:
                        print(f"[INDEXING FAILED] {f.name}: {str(e)}")
                else:
                    print(f"[SKIPPED INDEXING] No text found in {f.name}")

        except Exception as e:
            print(f"[UPLOAD ERROR]: {str(e)}")
            return JsonResponse(
                {"success": False, "error": "Upload failed."},
                status=500,
            )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        messages.success(request, "Documents uploaded and indexed successfully.")
        return redirect("documents:document_list")

    # =========================
    # 📄 SHOW PAGE
    # =========================
    folders = Folder.objects.filter(uploaded_by=user).order_by("name")

    return render(
        request,
        "documents/upload.html",
        {"folders": folders},
    )



# =========================
# 👁️ PREVIEW
# =========================

@login_required
def document_preview(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if document not in get_accessible_documents(request.user):
        return HttpResponseForbidden("Not allowed")

    return render(request, "documents/preview.html", {"document": document})


# =========================
# ⬇️ DOWNLOAD
# =========================

@login_required
def document_download(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if document not in get_accessible_documents(request.user):
        return HttpResponseForbidden("Not allowed")

    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1],
    )


# =========================
# 📁 MY DOCUMENTS
# =========================

@login_required
def my_documents(request):
    user = request.user
    folder_id = request.GET.get("folder")

    documents = Document.objects.filter(uploaded_by=user)

    if folder_id:
        documents = documents.filter(folder_id=folder_id)

    folders = Folder.objects.filter(uploaded_by=user)

    return render(
        request,
        "documents/my_documents.html",
        {
            "documents": documents.order_by("-created_at"),
            "folders": folders,
            "active_folder": folder_id,
        }
    )


# =========================
# 🗑️ DELETE DOCUMENT
# =========================

@login_required
def delete_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if not (request.user.is_superuser or document.uploaded_by == request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        document.file.delete(save=False)
        document.delete()

    return redirect("documents:my_documents")


# =========================
# 📂 CREATE FOLDER
# =========================

@login_required
def create_folder(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            Folder.objects.create(name=name, uploaded_by=request.user)

    return redirect("documents:my_documents")


@login_required
def bulk_delete_documents(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    ids = request.POST.getlist("document_ids")

    if not ids:
        messages.warning(request, "No documents selected.")
        return redirect("documents:document_list")

    # Superuser can delete everything selected
    if request.user.is_superuser:
        documents = Document.objects.filter(id__in=ids)
    else:
        # Normal users can only delete their own documents
        documents = Document.objects.filter(
            id__in=ids,
            uploaded_by=request.user
        )

    # Delete files safely
    for doc in documents:
        if doc.file:
            doc.file.delete(save=False)

    deleted_count = documents.count()
    documents.delete()

    if deleted_count:
        messages.success(request, f"{deleted_count} document(s) deleted.")
    else:
        messages.warning(request, "No documents were deleted.")

    return redirect("documents:document_list")

@login_required
def rename_folder(request, folder_id):
    folder = get_object_or_404(
        Folder,
        id=folder_id,
        uploaded_by=request.user
    )

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    new_name = request.POST.get("name", "").strip()

    if not new_name:
        messages.warning(request, "Folder name cannot be empty.")
        return redirect("documents:document_list")

    # Prevent duplicate folder names at same level
    if Folder.objects.filter(
        uploaded_by=request.user,
        parent=folder.parent,
        name=new_name
    ).exclude(id=folder.id).exists():
        messages.warning(request, "A folder with that name already exists.")
        return redirect("documents:document_list")

    folder.name = new_name
    folder.save()

    messages.success(request, "Folder renamed successfully.")
    return redirect("documents:document_list")


@login_required
def delete_folder(request, folder_id):
    folder = get_object_or_404(
        Folder,
        id=folder_id,
        uploaded_by=request.user
    )

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    # Optional safety: prevent deleting non-empty folders
    if folder.documents.exists() or folder.children.exists():
        messages.warning(
            request,
            "Cannot delete a folder that contains documents or subfolders."
        )
        return redirect("documents:document_list")

    folder.delete()

    messages.success(request, "Folder deleted successfully.")
    return redirect("documents:document_list")

@login_required
@require_POST
def move_document(request):
    user = request.user

    doc_id = request.POST.get("doc_id")
    folder_id = request.POST.get("folder_id")

    if not doc_id:
        return JsonResponse(
            {"success": False, "error": "Invalid document."},
            status=400,
        )

    # 🔒 Only fetch documents user owns (or superuser)
    if user.is_superuser:
        document = get_object_or_404(Document, id=doc_id)
    else:
        document = get_object_or_404(
            Document,
            id=doc_id,
            uploaded_by=user
        )

    # =========================
    # 📂 Move to Root (No Folder)
    # =========================
    if not folder_id:
        document.folder = None
        document.save(update_fields=["folder"])
        return JsonResponse({"success": True})

    # =========================
    # 📁 Validate Folder Ownership
    # =========================
    if user.is_superuser:
        folder = get_object_or_404(Folder, id=folder_id)
    else:
        folder = get_object_or_404(
            Folder,
            id=folder_id,
            uploaded_by=user
        )

    document.folder = folder
    document.save(update_fields=["folder"])

    return JsonResponse({"success": True})


