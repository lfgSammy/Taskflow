from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/',views.LoginView.as_view(), name='login'),
    path('workspace/', views.WorkspaceListView.as_view(), name='workspace-view'),
    path('workspace/<int:workspace_id>/', views.WorkspaceDetailView.as_view(), name='workspace-detail')
]