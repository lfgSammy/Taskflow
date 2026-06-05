from .models import (
    Workspace, Member, Project, Task, TaskHistory, Comment, Notification, User
)
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'bio', 'avatar', 'email','created_at']

class WorkSpaceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only = True)

    class Meta:
        model = Workspace
        fields = ['workspace_id', 'name', 'description', 'owner',
                  'created_at', 'updated_at']
        read_only_fields = ['owner', 'created_at', 'update_at']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['project_id','workspace', 'created_by', 'name',
                  'description', 'status','created_at', 'updated_at']
        
class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only = True)
    workspace = WorkSpaceSerializer(read_only = True)
    class Meta:
        model = Member
        fields = ['member_id', 'user','workspace', 'role',
                  'joined_at']

class TaskSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only= True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset = Project.objects.all(), source= 'project', write_only = True
    )
    assigned_to = UserSerializer(read_only= True)
    created_by = UserSerializer(read_only= True)

    class Meta:
        model = Task
        fields = ['Task_id', 'project', 'title', 'description',
                  'assigned_to','created_by', 'status','priority',
                  'due_date','created_at', 'updated_at']
        
        read_only_fields = ['created_by']

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only= True)

    class Meta:
        model = Comment
        fields = ['comment_id','task', 'author','content',
                  'created_at','updated_at']
        read_only_fields = ['author', 'task']

        
class TaskHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only= True)

    class Meta:
        model = TaskHistory
        fields = ['task_history_id', 'task','changed_by',
                  'old_value', 'new_value','changed_at']
        read_only_fields = ['task', 'changed_by', 'changed_at']
        
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['notification_id', 'user', 'message','is_read','created_at']
        read_only_fields = ['user','created_at']