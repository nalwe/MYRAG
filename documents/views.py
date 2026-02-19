from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from documents.models import Document, Folder
from documents.utils import get_accessible_documents
from documents.utils.text_extractor import extract_text_from_file
from accounts.models import OrganizationMember
from rag.indexer import index_document



# =========================
# 📄 DOCUMENT LIST
# =========================

@login_required
def document_list(request):
    user = request.user
    folder_id = request.GET.get("folder")
    query = request.GET.get("q", "").strip()

    if user.is_superuser:
        documents = Document.objects.all()
    else:
        documents = get_accessible_documents(user)

    folders = Folder.objects.filter(uploaded_by=user).order_by("name")

    active_folder = None
    if folder_id:
        active_folder = folders.filter(id=folder_id).first()
        if active_folder:
            documents = documents.filter(folder=active_folder)

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

    return render(
        request,
        "documents/list.html",
        {
            "documents": documents,
            "folders": folders,
            "active_folder": active_folder.id if active_folder else None,
            "query": query,
        }
    )


# =========================
# 📤 UPLOAD DOCUMENT
# =========================


@login_required
@require_http_methods(["GET", "POST"])
def document_upload(request):
    user = request.user

    member = (
        OrganizationMember.objects
        .select_related("organization")
        .filter(user=user)
        .first()
    )

    if not (user.is_superuser or (member and member.is_admin())):
        return HttpResponseForbidden("Not allowed")

    # =========================
    # 📤 HANDLE UPLOAD
    # =========================
    if request.method == "POST":
        files = request.FILES.getlist("files")

        if not files:
            return JsonResponse(
                {"success": False, "error": "No files selected."},
                status=400,
            )

        try:
            for f in files:
                extracted_text = ""
                try:
                    extracted_text = extract_text_from_file(f) or ""
                except Exception:
                    # Extraction failure should NOT break upload
                    pass

                Document.objects.create(
                    uploaded_by=user,
                    organization=None if user.is_superuser else member.organization,
                    is_public=user.is_superuser,
                    file=f,
                    extracted_text=extracted_text,
                )

                if doc.extracted_text:
                    index_document(doc)

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": "Upload failed."},
                status=500,
            )

        # 🔥 If AJAX request → return JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        # Fallback (non-AJAX form submit)
        messages.success(request, "Documents uploaded successfully.")
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
def move_document(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    doc_id = request.POST.get("doc_id")
    folder_id = request.POST.get("folder_id")

    if not doc_id:
        return JsonResponse({"success": False, "error": "Invalid document."})

    document = get_object_or_404(Document, id=doc_id)

    # Permission check
    if not (
        request.user.is_superuser or
        document.uploaded_by == request.user
    ):
        return HttpResponseForbidden("Not allowed")

    # Allow moving to root (no folder)
    if not folder_id:
        document.folder = None
        document.save(update_fields=["folder"])
        return JsonResponse({"success": True})

    # Validate target folder ownership
    folder = Folder.objects.filter(
        id=folder_id,
        uploaded_by=request.user
    ).first()

    if not folder:
        return JsonResponse({"success": False, "error": "Invalid folder."})

    document.folder = folder
    document.save(update_fields=["folder"])

    return JsonResponse({"success": True})


