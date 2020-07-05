from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'group': 'Сообщество',
            'text': 'Текст записи',
            'image': 'Изображение'
        }
        error_messages = {
            'text': {
                'required': 'Пожалуйста, заполните это поле'
            }
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст комментария'
        }
