from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from chat.models import Message, UserProfile
from chat.serializers import MessageSerializer, UserSerializer
from django.db.models import Q
import sqlite3


def index(request):
    if request.user.is_authenticated:
        return redirect('chats')
    if request.method == 'GET':
        return render(request, 'chat/index.html', {})
    if request.method == "POST":
        username, password = request.POST['username'], request.POST['password']
        user = authenticate(username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
        else:
            return render(request, 'chat/index.html', {'err': 'User does not exist'})
        return redirect('chats')


@csrf_exempt
def user_list(request, pk=None):
    """
    List all required users, or create a new user.
    """
    if request.method == 'GET':
        if pk:
            users = User.objects.filter(id=pk)
        else:
            sql1 = """SELECT receiver_id FROM chat_message WHERE sender_id=? AND message IS NOT NULL GROUP BY receiver_id"""
            sql2 = """SELECT sender_id FROM chat_message WHERE receiver_id=? AND message IS NOT NULL GROUP BY sender_id"""
            conn = sqlite3.connect('db.sqlite3')
            cur = conn.cursor()
            cur.execute(sql1, (request.user.id,))
            l1 = cur.fetchall()
            cur.execute(sql2, (request.user.id,))
            l2 = cur.fetchall()
            x = [i[0] for i in l1]
            y = [i[0] for i in l2]
            res = list(set(x + y))
            users = User.objects.filter(id__in=res).exclude(id=request.user.id)
            #users = User.objects.all()
        serializer = UserSerializer(users, many=True, context={'request': request})
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            user = User.objects.create_user(username=data['username'], password=data['password'])
            UserProfile.objects.create(user=user)
            return JsonResponse(data, status=201)
        except Exception:
            return JsonResponse({'error': "Something went wrong"}, status=400)


@csrf_exempt
def message_list(request, sender=None, receiver=None):
    """
    List all required messages, or create a new message.
    """
    if request.method == 'GET':
        messages = Message.objects.filter(sender_id=sender, receiver_id=receiver, is_read=False)
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        for message in messages:
            message.is_read = True
            message.save()
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


def register_view(request):
    """
    Render registration template
    """
    if request.user.is_authenticated:
        return redirect('chats')
    return render(request, 'chat/register.html', {})


def chat_view(request):
    if not request.user.is_authenticated:
        return redirect('index')

    if request.method == "GET":
        sql = """SELECT receiver_id FROM chat_message WHERE sender_id=? AND message IS NOT NULL GROUP BY receiver_id"""
        conn = sqlite3.connect('db.sqlite3')
        cur = conn.cursor()
        cur.execute(sql, (request.user.id,))
        l = cur.fetchall()
        x = [i[0] for i in l]
        users = User.objects.filter(id__in=x).exclude(id=request.user.id)
        # query = request.GET.get('q')
        # if query:
        #     users = User.objects.filter(username__contains=query)
        return render(request, 'chat/chat.html',
                      {'users': users})




def message_view(request, sender, receiver):
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        sql = """SELECT sender_id FROM chat_message WHERE sender_id=? AND receiver_id=? AND NOT(message IS NULL)"""
        conn = sqlite3.connect('db.sqlite3')
        cur = conn.cursor()
        cur.execute(sql, (sender, receiver))
        l = cur.fetchall()
        x = [i[0] for i in l]
        #users = User.objects.filter(id__in=x)

        return render(request, "chat/messages.html",
                      {'users': User.objects.exclude(id__in=x).exclude(username=request.user.username),
                       'receiver': User.objects.get(id=receiver),
                       'messages': Message.objects.filter(sender_id=sender, receiver_id=receiver) |
                                   Message.objects.filter(sender_id=receiver, receiver_id=sender)})

def search_view(request, username=None):
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        users = []
        query = request.GET.get('q')
        if query:
            users = User.objects.filter(username__contains=query)
        return render(request, "chat/search.html", {'users': users})
