from rest_framework import viewsets
from .models import Comment
from kerckhoff.packages.models import Package
from .serializers import CommentSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        package = Package.objects.get(slug=self.kwargs["package_slug"])
        serializer.save(created_by=self.request.user, package=package)
