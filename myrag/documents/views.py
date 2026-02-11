from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

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

    # Base queryset
    if user.is_superuser:
        documents = Document.objects.all()
    else:
        documents = get_accessible_documents(user)

    # Sidebar folders (Folder.owner is valid)
    folders = Folder.objects.filter(owner=user).order_by("name")

    # Folder filter
    active_folder = None
    if folder_id:
        active_folder = folders.filter(id=folder_id).first()
        if active_folder:
            documents = documents.filter(folder=active_folder)

    # Search
    if query:
        search_query = SearchQuery(query, config="english")
        documents = (
            documents
            .annotate(rank=SearchRank("search_vector", search_query))
            .filter(
                Q(rank__gte=0.1) |
                Q(title__icontains=query) |
                Q(extracted_text__icontains=query) |
                Q(file__icontains=query)
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
            document = Document.objects.create(
                uploaded_by=user,
                organization=None if user.is_superuser else member.organization,
                is_public=user.is_superuser,
                file=f,
            )

            try:
                text = extract_text_from_file(document.file.path) or ""
                document.extracted_text = text
                document.search_vector = SearchVector("extracted_text")
                document.save(update_fields=["extracted_text", "search_vector"])
            except Exception:
                pass

        messages.success(request, "Documents uploaded successfully.")
        return redirect("document_list")

    return render(request, "documents/upload.html")


# =========================
# 👁️ PREVIEW
# =========================

@login_required
def document_preview(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if document not in get_accessible_documents(request.user):
        return HttpResponseForbidden("Not allowed")

    return render(request, "documents/preview.html", {
        "document": document
    })


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
# 🗑️ DELETE
# =========================

@login_required
def delete_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    if not (request.user.is_superuser or document.uploaded_by == request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        document.file.delete(save=False)
        document.delete()

    return redirect("my_documents")


# =========================
# 📂 CREATE FOLDER
# =========================

@login_required
def create_folder(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            Folder.objects.create(
                name=name,
                owner=request.user
            )
    return redirect("my_documents")


# =========================
# 🔀 MOVE DOCUMENT
# =========================

@login_required
def move_document(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    doc_id = request.POST.get("doc_id")
    folder_id = request.POST.get("folder_id")

    document = get_object_or_404(Document, id=doc_id)

    if document.uploaded_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("Not allowed")

    folder = Folder.objects.filter(
        id=folder_id,
        owner=request.user
    ).first()

    document.folder = folder
    document.save(update_fields=["folder"])

    return JsonResponse({"success": True})
