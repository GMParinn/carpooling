from django.db import models


class Node(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Edge(models.Model):
    from_node = models.ForeignKey(Node, on_delete=models.CASCADE,
                                  related_name='outgoing_edges')
    to_node = models.ForeignKey(Node, on_delete=models.CASCADE,
                                related_name='incoming_edges')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_node', 'to_node')

    def __str__(self):
        return f"{self.from_node} → {self.to_node}"


class ServiceStatus(models.Model):
    """Singleton — row id=1 controls whether carpooling is open."""
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Service Status'
        verbose_name_plural = 'Service Status'

    def __str__(self):
        return f"Service {'Enabled' if self.enabled else 'Disabled'}"

    @classmethod
    def is_service_enabled(cls):
        status, _ = cls.objects.get_or_create(id=1, defaults={'enabled': True})
        return status.enabled
