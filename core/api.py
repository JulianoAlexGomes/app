from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Client
from .serializers import ClientSerializer

class ClientViewSet(ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Client.objects.filter(
            business=self.request.user.business
        )

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business
        )
