import re
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User

from .models import (
    Workspace, Project, Member, Task, TaskHistory, Comment
)

from .serializers import (
    WorkSpaceSerializer, ProjectSerializer, MemberSerializer,
    TaskSerializer, TaskHistorySerializer, CommentSerializer, NotificationSerializer
)


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    if not re.search(r'[0-9]', password):
        errors.append('Password must contain at least one letter')
    return errors

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        if not username or not password or not email:
            return Response({'error':'All fields are required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not validate_email(email):
            return Response({'error':'Invalid email format'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        password_errors = validate_password(password)
        if password_errors:
            return Response({'error': password_errors},
                            status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error':'Username already existed'},
                            status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email= email).exists():
            return Response({'error':'Email already existed'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':str(refresh.access_token),
            'refresh':str(refresh)
        }, status=status.HTTP_201_CREATED)
    
class LoginView(APIView):
    def post(self,request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password= password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access':str(refresh.access_token),
                'refresh':str(refresh)
            }, status=status.HTTP_200_OK)
        return Response({'error':'Invalid credentials'},
                        status=status.HTTP_401_UNAUTHORIZED)
    

def get_membership(user, workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        membership = Member.objects.filter(
            user=user, workspace=workspace).first()
        return workspace, membership
    except Workspace.DoesNotExist:
        return None, None

class WorkspaceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspaces = Workspace.objects.filter(
            members__user=request.user).distinct()
        serializer = WorkSpaceSerializer(workspaces, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WorkSpaceSerializer(data=request.data)
        if serializer.is_valid():
            workspace = serializer.save(owner=request.user)
            Member.objects.create(
                user=request.user,
                workspace=workspace,
                role='owner'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = WorkSpaceSerializer(workspace)
        return Response(serializer.data)

    def patch(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if membership.role not in ['owner', 'admin']:
            return Response({'error': 'You do not have permission to update this workspace'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = WorkSpaceSerializer(workspace, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if membership.role != 'owner':
            return Response({'error': 'Only owners can delete this workspace'},
                            status=status.HTTP_403_FORBIDDEN)
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
def get_membership(user, workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        membership = Member.objects.filter(
            user=user, workspace=workspace).first()
        return workspace, membership
    except Workspace.DoesNotExist:
        return None, None


def get_member(workspace_id, member_id):
    return Member.objects.filter(
        id=member_id, workspace_id=workspace_id).first()


class MemberListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        members = Member.objects.filter(workspace=workspace)
        serializer = MemberSerializer(members, many=True)
        return Response(serializer.data)

    def post(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if membership.role not in ['owner', 'admin']:
            return Response({'error': 'Only owners or admins can invite members'},
                            status=status.HTTP_403_FORBIDDEN)
        username = request.data.get('username')
        role = request.data.get('role', 'member')
        user = User.objects.filter(username=username).first()
        if not user:
            return Response({'error': 'User not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if Member.objects.filter(user=user, workspace=workspace).exists():
            return Response({'error': 'User is already a member'},
                            status=status.HTTP_400_BAD_REQUEST)
        if membership.role == 'admin' and role == 'owner':
            return Response({'error': 'Admins cannot assign owner role'},
                            status=status.HTTP_403_FORBIDDEN)
        new_member = Member.objects.create(
            user=user, workspace=workspace, role=role)
        serializer = MemberSerializer(new_member)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, member_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        member = get_member(workspace_id, member_id)
        if not member:
            return Response({'error': 'Member not found'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = MemberSerializer(member)
        return Response(serializer.data)

    def delete(self, request, workspace_id, member_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error': 'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if membership.role not in ['owner', 'admin']:
            return Response({'error': 'Only admins or owners can remove members'},
                            status=status.HTTP_403_FORBIDDEN)
        member = get_member(workspace_id, member_id)
        if not member:
            return Response({'error': 'Member not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if member.role == 'owner':
            return Response({'error': 'Owner cannot be removed'},
                            status=status.HTTP_403_FORBIDDEN)
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error':'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        projects = Project.objects.filter(workspace=workspace)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, workspace_id):
        workspace, membership = get_membership(request.user, workspace_id)
        if not membership:
            return Response({'error':'Workspace not found'},
                            status=status.HTTP_404_NOT_FOUND)
        if membership.role not in ['owner','admin']:
            return Response({'error':'Only owners and admin can create project'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = ProjectSerializer(data= request.data)
        if serializer.is_valid():
            serializer.save(workspace= workspace, created_by= request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.error, status=status.HTTP_400_BAD_REQUEST)
    
class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]
