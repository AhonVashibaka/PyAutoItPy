#coding=utf-8
"""
Создан: 18.09.2014

Автор: Ахон Вашибака (AhonVashibaka@gmail.com)

Версия: 0.9.6 beta
"""
import time
from os import system
from PyAutoItPy import AutoItX, WinHandle, WinState, MB_Flags

#Запускаем блокнот отдельным процессом
CallRes=system('start notepad')
#Если проблемы, выходим.
if CallRes!=0:
    print('Невозможно запустить блокнот!')
    exit(CallRes)

print ('Блокнот запущен')
#Создаем экземпляр AutoItX
Automat=AutoItX()
#Это заголовок для поиска окна в формате AutoIt
Title='[CLASS:Notepad]'
#Это идентификатор контрола в формате AutoIt
Control='[CLASS:Edit; INSTANCE:1]'
#Ну и пока пустой Handle
Handle=None
#Ждем появления окна, вдруг еще не открылось
Opened=Automat.WinWait(Title,5)
#Выходим, если не дождались открытия блокнота.
if not Opened:
    print('Что-то блокнот тормозит... Наверное, нужен апгрейд!')
    exit(-1)
#Если открылось - получаем Handle, чтобы работать с конкретно данным окном.
Handle=WinHandle(Automat.WinGetHandle(Title))
#Выходим, если не удалось получить Handle окна.
if not Handle:
    print('Невозможно получить Handle блокнота!')
    exit(-1)
#Итак, блокнот готов, его Handle получен, выводим Handle, и
print ('Handle окна блокнота: {}'.format(Handle))
#получаем состояние окна, тут же разбираем его.
State=WinState(Automat.WinGetState(Handle))
print ('Состояние окна блокнота: {} {}'.format(State.StateNum, State.StateString))
#Запоминаем положение и размер окна блокнота
NotepadRect=Automat.WinGetPos(Handle)
#Активируем окно, иначе некоторые функции могут не сработать
Automat.WinActivate(Handle)
#Уж совсем на всякий случай перемещаем фокус ввода в нужный контрол.
Automat.ControlFocus(Handle,Control)
#Бьем баклуши
time.sleep(1)
#Отсылаем "Привет!".
Automat.ControlSetText(Handle, Control, 'Привет!')
#Пинаем банки
time.sleep(1)
#Делаем удаление как бы с клавиатуры 
Automat.Send('{END}')
Automat.Send('{BACKSPACE}',7)
#Бьем лежачего
time.sleep(1)
#Делаем красивый ввод с клавиатуры типа "Ой, призраки!"
Automat.ControlSend(Handle, Control, 'Попробуй поймать меня{!}')
#Ковыряем в носу
time.sleep(1)
#Волшебный фокус с исчезновением окна.
for i in range(254,0,-1):
    Automat.WinSetTrans(Handle, i)
    time.sleep(0.005)
#Перепрятываем окно
Automat.WinMove(Handle, 100, 100, 350, 75)
#Наводим ужас
time.sleep(1)
#Кастуем на окно воскрешение
for i in range(1,256):
    Automat.WinSetTrans(Handle, i)
    time.sleep(0.005)
#Упиваемся собственной значимостью
time.sleep(1)
#А теперь - веселые гонки в духе "Том и Джерри". В роли Джерри - блокнот, в роли Тома - курсор. Хотя логичнее было бы наоборот:)
#Для начала определяем паузу между перемещениями.
Interval=1
#Запоминаем время начала погони.
Start=time.clock()
#Задаем время окончания представления (через 10 секунд)
Finish=Start+10
#Вперед!
while Finish-Start>=0:
    #Перемещаем Джерри(блокнот) в следующую точку.
    Automat.WinMove(Handle,500,100)
    #Перемещаем Тома(курсор) в точку позади.
    Automat.MouseMove(100, 100)
    #Красивый стоп-кадр в духе "Матрицы".
    time.sleep(Interval)
    #И так еще три раза.
    Automat.WinMove(Handle,500,500)
    Automat.MouseMove(500, 100)
    time.sleep(Interval)
    Automat.WinMove(Handle,100,500)
    Automat.MouseMove(500, 500)
    time.sleep(Interval)
    Automat.WinMove(Handle,100,100)
    Automat.MouseMove(100, 500)
    time.sleep(Interval)
    #Смотрим на часы
    Start=time.clock()
#Уф! Погоня окончена, передохнем!
time.sleep(1)
#Теперь вернем блокнот на место.
Automat.WinMove(Handle, NotepadRect.X, NotepadRect.Y, NotepadRect.WIDTH, NotepadRect.HEIGHT)
#И очистим его содержимое.
Automat.ControlSetText(Handle, Control, '')
#Прочтем его состояние.
State.SetState(Automat.WinGetState(Handle))
#И сообщим итоги зрителю через MessageBox.
Automat.MsgBox(
               'Проверка',
               'Ура! Тест завершен!\nБлокнот на место возвращен!\nВот на прощание окна блокнота состояние:\n{}\n{}'.format(State.StateNum, State.StateString),
               MB_Flags.MB_ICONWARNING|MB_Flags.MB_OK|MB_Flags.MB_SYSTEMMODAL
               )
#Все, представление окончено, занавес! Закрываем блокнот.
Automat.WinClose(Handle)
