# Импортируем:

import os
# Возможность отправки статуса в качестве ответа
from django.http import HttpResponse
# Тоже формы ответа сервера
from django.shortcuts import render, redirect
# Класс, от которого нужно наследовать view'шки
from django.views import View
# Записи базы данных
from .models import Video, Channel, Comment, Category
from django.contrib.auth.models import User
# Нечёткое сравнение
from fuzzywuzzy import fuzz
# Модуль для получения отдельного кадра из видео
import cv2
from django.core.files.storage import FileSystemStorage


class IndexView(View):
    """Главная страница"""

    @staticmethod
    def get(request):
        videos = Video.objects.all()[::-1]
        return render(request, 'main/index.html', {"videos": videos})


class VideoView(View):
    """Страница определённого видео"""

    @staticmethod
    def get(request, name):
        reaction = 'none'
        video = Video.objects.get(name=name)
        if request.user.is_authenticated:
            try:
                video.liked_by.get(username=request.user.username)
                reaction = 'like'
            except:
                try:
                    video.disliked_by.get(username=request.user.username)
                    reaction = 'dislike'
                except:
                    reaction = 'none'
        return render(request, 'main/video.html', {"video": video, "reaction": reaction})


class ChannelView(View):
    """Страница канала"""

    @staticmethod
    def get(request, name):
        # Получаем объект канала
        channel = Channel.objects.get(name=name)
        # Получаем общее кол-во видео
        count = len(channel.video_set.all())
        # Получаем все доступные категории (необходимо для работы формы загрузки видео внизу страницы канала)
        categories = Category.objects.all()
        return render(request, 'main/channel.html', {"channel": channel, "count": count, "categories": categories})


class AddCommentView(View):
    """Добавление комментария к видео"""

    @staticmethod
    def post(request):
        # Начинаем готовить ответ
        response = HttpResponse()
        # Небольшая защита (долго писать от чего)
        try:
            # Получаем объект пользователя из базы данных
            user = User.objects.get(username=request.user.username)
            # Получаем объект видео
            video_name = request.POST.get("video")
            video = Video.objects.get(name=video_name)
            # Получаем текст будущего комментария
            text = request.POST.get("text")
            # Создаём запись о существовании комментария в базе данных
            comment = Comment.objects.create(
                user=user,
                video=video,
                text=text
            )
            comment.save()
            # Записываем информацию об успешном выполнении запроса
            response.status_code = 200
        except:
            response.status_code = 404
        # Возвращаем статус
        return response


class ProfileView(View):
    """Профиль(личный кабинет) пользователя"""

    @staticmethod
    def get(request):
        # Смотрим, вошёл ли пользователь и пропускаем только вошедших, иначе отправляем на страницу входа
        if request.user.is_authenticated:
            # Получаем список каналов, владельцем которых является пользователь
            try:
                channel_list = Channel.objects.filter(
                    owner__username=request.user.username)
                are_channels = True
            except:
                print("no channels")
                channel_list = []
                are_channels = False
            # Возвращаем результат
            return render(request, 'main/profile.html', {"channel_list": channel_list, "are_channels": are_channels})
        else:
            return redirect('/accounts/login')


class UploadVideoView(View):
    """Загрузка на сайт нового видео"""

    @staticmethod
    def post(request):
        # Создаём объект ответа
        response = HttpResponse()
        # Получаем данные из запроса и из базы данных
        name = request.POST.get('name')
        description = request.POST.get('description')
        video = request.FILES.get('video')
        category_name = request.POST.get('category')
        category = Category.objects.get(name=category_name)
        channel_name = request.POST.get('channel')
        poster = request.FILES.get('poster')
        channel = Channel.objects.get(name=channel_name)
        # Создаём запись о видео в базе данных
        new_video = Video.objects.create(
            name=name,
            description=description,
            video=video,
            poster=poster,
            category=category,
            channel=channel
        )
        new_video.save()
        response.status_code = 200
        # Возвращаем ответ
        return response


class Search(View):
    """Поиск по сайту"""

    @staticmethod
    def get(request):
        # Получаем текст поиска
        request_text = request.GET.get('request_text')
        # Получаем видео
        videos = Video.objects.all()
        # Объявляем массив подходящих видео
        correct_videos = []
        # Обрабатываем массив видео
        for video in videos:
            # Альтернативная версия условия поиска
            # if (fuzz.ratio(video.name.lower(), request_text.lower()) > 45) or (fuzz.ratio(request_text.lower(),
            # video.description.lower()) > 45):

            # Если найдено нужное кол-во совпадений запроса и названиявидео считаем его подходящим
            if fuzz.ratio(video.name.lower(), request_text.lower()) > 45:
                correct_videos += [video]
        # Возвращаем ответ
        return render(request, 'main/search.html', {"correct_videos": correct_videos})


class CreateChannel(View):
    """Создание канала"""

    @staticmethod
    def get(request):
        """Страница с формой для заполнения"""
        return render(request, 'main/create-channel.html', {})

    @staticmethod
    def post(request):
        """Непосредственно создание канала"""

        # Проверяем, вошёл ли пользователь
        if request.user.is_authenticated:
            # Получаем данные из запроса
            name = request.POST.get("name")
            description = request.POST.get("description")
            owner = User.objects.get(username=request.user.username)
            logo = request.FILES.get('logo')
            # Создаём канал
            new_channel = Channel.objects.create(
                name=name,
                description=description,
                owner=owner,
                logo=logo
            )
            new_channel.save()
            # Возвращаем ответ
            response = HttpResponse()
            response.status_code = 200
            return response
        else:
            return redirect("/accounts/login")


class DropChannel(View):
    """Удаление канала"""

    @staticmethod
    def post(request):
        # Проверяем, вошёл ли пользователь
        if request.user.is_authenticated:
            # Получаем введённо имя канала
            channel_name = request.POST.get('channel-name')
            # Начинаем готовить ответ пользователю
            response = HttpResponse()
            # Пробуем получить объект базы данных
            try:
                channel = Channel.objects.get(name=channel_name)
            except:
                # Если не получается, значит введено неверное имя канала
                response.status_code = 405
                return response
            # Проверяем, является ли пользователь владельцем канала
            if request.user.username == channel.owner.username:
                # Удаляем объект
                channel.delete()
                response.status_code = 200
                return response
            else:
                response.status_code = 405
                return response
        else:
            return redirect('/accounts/login')


class DropVideo(View):
    """Удаление видео"""

    @staticmethod
    def post(request):
        # Проверяем, вошёл ли пользователь
        if request.user.is_authenticated:
            # Получаем введённо имя видео
            video_name = request.POST.get('video-name')
            # Начинаем готовить ответ пользователю
            response = HttpResponse()
            # Пробуем получить объект базы данных
            try:
                video = Video.objects.get(name=video_name)
            except:
                # Если не получается, значит введено неверное имя канала
                response.status_code = 405
                return response
            # Проверяем, является ли пользователь владельцем канала, на котором рамещено видео
            if request.user.username == video.channel.owner.username:
                # Удаляем объект
                video.delete()
                response.status_code = 200
                return response
            else:
                response.status_code = 405
                return response
        else:
            return redirect('/accounts/login')


class ChangeVideoPage(View):
    """Страница изменения видео"""

    @staticmethod
    def get(request, video):
        # Пробуем получить видео
        try:
            video = Video.objects.get(name=video)
            # Получаем список доступных категорий
            categories = Category.objects.all()
            # Возвращаем отрендеренную страницу
            return render(request, 'main/change-video.html', {"video": video, "categories": categories})
        except:
            # Если не получается, то отправляем пользователя на главную страницу
            return redirect('/')


class ChangeVideo(View):
    """Изменение видео"""

    @staticmethod
    def post(request):
        # Получаем данные из запроса
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = request.POST.get('category')
        video_id = request.POST.get('id')
        # Создаём объект ответа
        response = HttpResponse()
        # Пробуем получить видео
        try:
            video = Video.objects.get(id=video_id)
        except:
            response.status_code = 404
            return response
        # Применяем изменения названия и описания
        video.name = name
        video.description = description
        # Немного безопасности
        try:
            category = Category.objects.get(name=category)
        except:
            response.status_code = 405
            return response
        # Применяем изменения категории
        video.category = category
        # Проверяем, были ли внемены изменения файла видео и постера, если да, то применяем
        try:
            file_video = request.FILES.get('video')
            if file_video is not None:
                video.video = file_video
        except:
            pass
        try:
            poster = request.FILES.get('poster')
            if poster is not None:
                video.poster = poster
        except:
            pass
        # Сохраняем изменения
        video.save()
        # Отправляем информацию об успешном выполнении запроса
        response.status_code = 200
        return response


class ChangeChannelPage(View):
    """Страница изменения канала"""

    @staticmethod
    def get(request, channel):
        try:
            channel = Channel.objects.get(name=channel)
        except:
            pass
        return render(request, 'main/change-channel.html', {"channel": channel})


class ChangeChannel(View):
    """Изменение канала"""

    @staticmethod
    def post(request):
        name = request.POST.get('name')
        description = request.POST.get('description')
        channel_id = request.POST.get('id')
        response = HttpResponse()
        try:
            channel = Channel.objects.get(id=channel_id)
        except:
            response.status_code = 404
            return response
        channel.name = name
        channel.description = description
        try:
            logo = request.FILES.get('logo')
            if logo is not None:
                channel.logo = logo
        except:
            pass
        channel.save()
        response.status_code = 200
        return response


class LikeVideo(View):
    """Возможность ставить лайк или дизлайк видео"""

    @staticmethod
    def post(request):
        # Получаем объект пользователя
        user = User.objects.get(username=request.user.username)
        # Получаем имя нужного видео
        name = request.POST.get('name')
        type_of_operation = request.POST.get('type')
        # Создаём объект ответа
        response = HttpResponse()
        # Пробуем получить объект видео в базе данных
        try:
            video = Video.objects.get(name=name)
        except:
            response.status_code = 405
            return response
        # Проверяем, не ставил ли пользователь оценку видео раньше и если ставил, то какую
        liked = False
        disliked = False
        try:
            video.liked_by.get(username=request.user.username)
            liked = True
        except:
            pass
        try:
            video.disliked_by.get(username=request.user.username)
            disliked = True
        except:
            pass
        # Обрабатываем полученные ранее данные
        if (not liked) and (not disliked):
            # Если ещё не ставил оценки, то ставим нужную
            if request.POST.get('type') == 'like':
                video.likes += 1
                video.liked_by.add(user)
                response.status_code = 200
            elif request.POST.get('type') == 'dislike':
                video.dislikes += 1
                video.disliked_by.add(user)
                response.status_code = 200
            else:
                # Если не лайк, и не дизлайк, то сообщаем об ошибке
                print("error")
                response.status_code = 405
                return response
        elif (not liked) and disliked and (type_of_operation == 'like'):
            # Если хочет изменить оценку с дизлайка на лайк
            video.disliked_by.remove(user)
            video.liked_by.add(user)
            video.dislikes -= 1
            video.likes += 1
            # Статус ответа нужен для нужного сообщения пользователю и изменения элементов страницу (см.
            # static/js/video_script.js)
            response.status_code = 202
        elif liked and (not disliked) and (type_of_operation == 'dislike'):
            # Если хочет изменить оценку с лайка на дизлайк
            video.disliked_by.add(user)
            video.liked_by.remove(user)
            video.dislikes += 1
            video.likes -= 1
            # Статус ответа нужен для нужного сообщения пользователю и изменения элементов страницу (см.
            # static/js/video_script.js)
            response.status_code = 203
        elif liked and (type_of_operation == 'like'):
            # Если хочет поставить второй лайк
            response.status_code = 201
        elif disliked and (type_of_operation == 'dislike'):
            # Если хочет поставить второй дизлайк
            response.status_code = 201
        else:
            # Если какая-то другая ситуация, то сообщаем об ошибке
            print("error")
            response.status_code = 405
        # Сохраняем изменения
        video.save()
        # Возвращаем ответ
        return response


class Subscribe(View):
    """Осуществление подписки на канал"""

    @staticmethod
    def post(request):
        # Начинаем готовить ответ
        response = HttpResponse()
        # Получаем данные из запроса и базы данных
        channel_name = request.POST.get('channel_name')
        user = User.objects.get(username=request.user.username)
        channel = Channel.objects.get(name=channel_name)
        # Смотрим, подписан ли пользователь на канал
        try:
            # Если да, то отменяем подписку
            channel.subscribers.get(username=request.user.username)
            channel.subscribers.remove(user)
            response.status_code = 201
        except:
            # Если нет, то оформляем подписку
            channel.subscribers.add(user)
            channel.save()
            response.status_code = 200
        # Возвращаем ответ
        return response