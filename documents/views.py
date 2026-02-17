from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank

from documents.models import Document, Folder
from documents.utils import get_accessible_documents
from documents.utils.text_extractor import extract_text_from_file
from accounts.models import OrganizationMember


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

    folders = Folder.objects.filter(owner=user).order_by("name")

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

    if request.method == "POST":
        files = request.FILES.getlist("files")

        for f in files:
            extracted_text = ""
            try:
                extracted_text = extract_text_from_file(f) or ""
            except Exception:
                pass

            document = Document(
                uploaded_by=user,
                organization=None if user.is_superuser else member.organization,
                is_public=user.is_superuser,
                file=f,
                extracted_text=extracted_text,
            )

            document.save()  # search_vector handled in model

        messages.success(request, "Documents uploaded successfully.")
        return redirect("documents:document_list")

    return render(request, "documents/upload.html")


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

    folders = Folder.objects.filter(owner=user)

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
            Folder.objects.create(name=name, owner=request.user)

    return redirect("documents:my_documents")
