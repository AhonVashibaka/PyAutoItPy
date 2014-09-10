#coding=utf-8
"""
Создан: 17.12.2012

Автор: Ахон Вашибака (AhonVashibaka@gmail.com)

Версия: 0.9.6.11 beta
"""

# -------------------------------------------------------------------------------

from ctypes import WinDLL, \
    DEFAULT_MODE, \
    create_unicode_buffer, \
    byref, \
    POINTER, \
    pointer, \
    c_wchar_p, \
    c_longlong, \
    c_ulonglong, \
    c_long, \
    c_ulong, \
    c_int, \
    c_uint, \
    c_void_p, \
    windll

from ctypes.wintypes import HWND
from collections import OrderedDict, namedtuple
import os
from functools import wraps
from time import sleep, perf_counter
from sys import maxsize as sysMaxSize
# -------------------------------------------------------------------------------
#Определения
#: Тип для сохранения координат точки.
WinPoint = namedtuple('WinPoint', 'X, Y')
#: Тип для cохранения координат окна.
WinRect = namedtuple('WinRect', 'X, Y, WIDTH, HEIGHT')
#: Лямбда для преобразования строки, возвращаемой WinGetHandle в формат AutoIt.
WinHandle = lambda x: '[HANDLE:{}]'.format(x)
#: Служебный тип для флагов установки состояния окна функцией WinSetState.
SetStateValues = namedtuple('SetStateValues',
                            '''
                            HIDE, SHOW, DISABLE, ENABLE, LOCK, MAXIMIZE, MINIMIZE, RESTORE, SHOWDEFAULT,
                            SHOWMAXIMIZED, SHOWMINIMIZED, SHOWMINNOACTIVE, SHOWNA, SHOWNOACTIVATE, SHOWNORMAL, UNLOCK
                            ''')
#: Именованный массив для задания флагов состояний при использовании WinSetState.
SW = SetStateValues(0, 5, 65, 64, 66, 3, 6, 9, 10, 3, 2, 7, 8, 4, 1, 67)
#: Массив для преобразования числа, возвращаемого MouseGetCursor в имя курсора.
MouseGetCursorValue = (
    'UNKNOWN', 'APPSTARTING', 'ARROW', 'CROSS', 'HELP', 'IBEAM', 'ICON', 'NO', 'SIZE', 'SIZEALL', 'SIZENESW', 'SIZENS',
    'SIZENWSE', 'SIZEWE', 'UPARROW', 'WAIT')
#: Служебные типы для работы с PixelSearch.
PixelSearchRetType = c_int * 2
PixelSearchRetTypeP = POINTER(PixelSearchRetType)
#: Служебный тип для интерпретации значений, возвращаемых MsgBox.
MsgBoxRetType = namedtuple('MsgBoxRetType',
                           'IDOK, IDCANCEL, IDABORT, IDRETRY, IDIGNORE, IDYES, IDNO, IDTRYAGAIN, IDCONTINUE')
#: Именованный массив для интерпретации значений, возвращаемых MsgBox.
MB_RetVal = MsgBoxRetType(1, 2, 3, 4, 5, 6, 7, 10, 11)
#: Служебный тип для флагов MsgBox.
MsgBoxFlagsType = namedtuple('MsgBoxFlagsType',
                             '''
                             MB_OK, MB_OKCANCEL, MB_ABORTRETRYIGNORE, MB_YESNOCANCEL, MB_YESNO, MB_RETRYCANCEL,
                             MB_CANCELTRYCONTINUE, MB_HELP, MB_ICONERROR, MB_ICONSTOP, MB_ICONHAND, MB_ICONQUESTION,
                             MB_ICONWARNING, MB_ICONEXCLAMATION, MB_ICONINFORMATION, MB_ICONASTERISK, MB_DEFBUTTON1,
                             MB_DEFBUTTON2, MB_DEFBUTTON3, MB_DEFBUTTON4, MB_APPLMODAL, MB_SYSTEMMODAL, MB_TASKMODAL,
                             MB_SETFOREGROUND, MB_DEFAULT_DESKTOP_ONLY, MB_TOPMOST, MB_RIGHT, MB_RTLREADING,
                             MB_SERVICE_NOTIFICATION
                             ''')
#: Именованный массив для задания флагов при вызове MsgBox.
MB_Flags = MsgBoxFlagsType(0, 1, 2, 3, 4, 5, 6, 0x4000,
                           0x10, 0x10, 0x10, 0x20, 0x30, 0x30, 0x40, 0x40,
                           0, 0x100, 0x200, 0x300,
                           0, 0x1000, 0x2000,
                           0x10000, 0x20000, 0x40000, 0x80000, 0x100000, 0x200000)
#-------------------------------------------------------------------------------


class CustomWinDLL(WinDLL):
    """
        Класс по загрузке и использованию DLL, аналогичен стандартному классу WinDLL (получен наследованием)
        из модуля ctypes.
        Параметры конструктора:

        * ProtoDict - основное отличие, словарь с параметрами процедур в DLL, формат такой:
            {
                    'Имя фунции':{
                                    'ReturnType':строка с именем типа возвр. значения из ctypes, напрмер: 'c_long',
                                    'ArgTypes':строка со спиком типов входных параметров в скобочках, например:
                                    '(c_wchar_p, c_long, c_long, c_long, c_long)'
                                },
                    'Имя след. функции':{
                                            'ReturnType':строка с именем типа возвр. значения из ctypes, напрмер:
                                            'c_void_p',
                                            'ArgTypes':строка со спиком типов входных параметров в скобочках, например:
                                            '(c_ulong, c_int, c_uint)',
                                                для функций без параметров вписать просто '()'.
                                        },
                и т.д.
            }
        * name - от предка, путь к DLL,
        * mode=DEFAULT_MODE - от предка, режим работы с DLL,
        * handle=None - от предка, DLL handle
        * use_errno=False - от предка,
        * use_last_error=False - от предка.
    """

    def __init__(self, ProtoDict, name, mode=DEFAULT_MODE, handle=None, use_errno=False, use_last_error=False):
        super().__init__(name, mode, handle, use_errno, use_last_error)
        self.__ProtoDict__ = ProtoDict
        for Proto in self.__ProtoDict__:
            #print ('{}\n{}'.format(self.__ProtoDict__[Proto]['ReturnType'], self.__ProtoDict__[Proto]['ArgTypes']))
            exec('self.{}.restype = {}'.format(Proto, self.__ProtoDict__[Proto]['ReturnType']))
            exec('self.{}.argtypes = {}'.format(Proto, self.__ProtoDict__[Proto]['ArgTypes']))


#-------------------------------------------------------------------------------

class WinState:
    """
        Класс для хранения и преобразования состояния окна, возвращаемого функцией WinGetState.

        Параметры конструктора:

        * State - начальное значение состояния в числовом или строковом виде, подробности далее.

        Свойства:

        * StateNum=None - числовое значение состояния (возвращается функцией WinGetState), гененрируется автоматически
        при задании состояния методом SetState со строковым значанием
        * StateString=None - строковое описание состояния, гененрируется автоматически при задании состояния методом
        SetState с числовым значанием,
            содержит список активных признаков(см. ниже), разделенных запятыми, например:
            'EXISTS, VISIBLE, ENABLED'
        * EXISTS=False - логический признак существования окна.
        * VISIBLE=False - логический признак видисти окна.
        * ENABLED=False - логический признак того, что окно включено.
        * ACTIVE=False - логический признак активности окна.
        * MINIMIZED=False - логический признак того, что окно свернуто.
        * MAXIMIZED=False - логический признак того, что окно раширено до масимальных размеров.

        Логические признаки формируются автоматически при задании состояния методом SetState.
        Если напрямую поменять значения логических признаков, то автоматически изменятся значения StateNum
        и StateString.
        Имеются так же методы сравнения двух состояний, что позволяет сопоставлять экземпляры класса, содержащие
        значения, при помощи операторов "==", "!=", ">=", "<=", ">", "<".
    """
    StateNum = None
    StateString = None
    EXISTS = False
    VISIBLE = False
    ENABLED = False
    ACTIVE = False
    MINIMIZED = False
    MAXIMIZED = False
    __StatesDict__ = OrderedDict((
        ('EXISTS', 1),
        ('VISIBLE', 2),
        ('ENABLED', 4),
        ('ACTIVE', 8),
        ('MINIMIZED', 16),
        ('MAXIMIZED', 32),
    ))

    #-------------------------------------------------------------------------------

    def __init__(self, State):
        self.SetState(State)

    #-------------------------------------------------------------------------------

    def __setattr__(self, Name, Value):
        """
            Внутренний метод, автоматизирующий обновление значений StateNum и StateString
            при изменении логических признаков.
        """
        super().__setattr__(Name, Value)
        if self.__StatesDict__ and Name in self.__StatesDict__:
            self.__UpdateFromBoolean__()

    #-------------------------------------------------------------------------------
    #Далее идут методы для операторов "==", "!=", ">=", "<=", ">", "<".

    #"<"
    def __lt__(self, SecondState):
        x = 0
        y = 0
        z = 0
        for Param in self.__StatesDict__:

            if self.__dict__[Param]:
                x += 1
            if SecondState.__dict__[Param]:
                y += 1
            if self.__dict__[Param] and SecondState.__dict__[Param]:
                z += 1
        if y > z and y > x:
            return True
        else:
            return False

    #"<="
    def __le__(self, SecondState):
        x = 0
        y = 0
        z = 0

        for Param in self.__StatesDict__:
            if self.__dict__[Param]:
                x += 1
            if SecondState.__dict__[Param]:
                y += 1
            if self.__dict__[Param] and SecondState.__dict__[Param]:
                z += 1
        if z == y == x or (y > z and y > x):
            return True
        else:
            return False

    #"=="
    def __eq__(self, SecondState):
        Res = True
        for Param in self.__StatesDict__:
            '''
            if Param=='ACTIVE':
                continue
            '''
            if self.__dict__[Param] != SecondState.__dict__[Param]:
                print(Param, self.__dict__[Param], SecondState.__dict__[Param])
                Res = False
        return Res

    #"!="
    def __ne__(self, SecondState):
        Res = False
        for Param in self.__StatesDict__:
            '''
            if Param=='ACTIVE':
                continue
            '''
            if self.__dict__[Param] != SecondState.__dict__[Param]:
                Res = True
        return Res

    #">="
    def __ge__(self, SecondState):
        x = 0
        y = 0
        z = 0
        for Param in self.__StatesDict__:
            if self.__dict__[Param]:
                x += 1
            if SecondState.__dict__[Param]:
                y += 1
            if self.__dict__[Param] and SecondState.__dict__[Param]:
                z += 1
        if z > 0 and z == y <= x:
            return True
        else:
            return False

    #">"
    def __gt__(self, SecondState):
        x = 0
        y = 0
        z = 0
        for Param in self.__StatesDict__:
            if self.__dict__[Param]:
                x += 1
            if SecondState.__dict__[Param]:
                y += 1
            if self.__dict__[Param] and SecondState.__dict__[Param]:
                z += 1
        if z > 0 and z <= y < x:
            return True
        else:
            return False

    #Конец определений методов для операторов "==", "!=", ">=", "<=", ">", "<".
    #-------------------------------------------------------------------------------

    def SetState(self, State):
        """
            Метод задания значения состояния окна, принимает число, возвращаемое WinGetState,
            или строку , содержащую список активных признаков, например:
            'EXISTS, VISIBLE, ENABLED, ACTIVE'
        """
        if isinstance(State, str):
            self.StateString = State
            self.StateNum = self.__StringToState__(State)
        elif isinstance(State, int):
            self.StateString = self.__StateToString__(State)
            self.StateNum = State
        else:
            raise TypeError('Состояние окна должно иметь тип "str" или "int", сейчас это "{}"'.format(type(State)))

    #-------------------------------------------------------------------------------

    def __StateToString__(self, StateNum):
        StateList = []
        for State in self.__StatesDict__.items():
            if StateNum & State[1] == State[1]:
                StateList.append(State[0])
                self.__dict__[State[0]] = True
            else:
                self.__dict__[State[0]] = False
        Res = ','.join(StateList) if len(StateList) > 0 else None

        return Res

    #-------------------------------------------------------------------------------

    def __StringToState__(self, StrState):
        Res = 0
        StateList = list(S.strip().upper() for S in str(StrState).split(','))
        for ST in self.__StatesDict__:
            if ST in StateList:
                Res |= self.__StatesDict__[ST]
                self.__dict__[ST] = True
            else:
                self.__dict__[ST] = False
        return Res

    #-------------------------------------------------------------------------------

    def __UpdateFromBoolean__(self):
        ResNum = 0
        ResStrList = []
        for ParName, ParNum in self.__StatesDict__.items():
            if self.__dict__[ParName]:
                if ParName == 'MINIMIZED':
                    if self.__dict__['MAXIMIZED']:
                        self.__dict__['MAXIMIZED'] = False
                elif ParName == 'MAXIMIZED':
                    if self.__dict__['MINIMIZED']:
                        self.__dict__['MINIMIZED'] = False
                ResNum |= ParNum
                ResStrList.append(ParName)

        self.StateNum = ResNum
        self.StateString = ','.join(ResStrList)


#-------------------------------------------------------------------------------

class WinParams:
    """
        Класс для хранения параметров окна.

        Параметры конструктора:
            * Header - заголовок окна.
            * Class=None - класс окна.
            * Handle=None - Handle окна.

        Свойства:
            * Header=None - заголовок окна.
            * Class=None - класс окна.
            * Handle=None - Handle окна.
            * Rectangle=None - Значение с типом WinRect, содержащее размеры окна.
            * ClientRectangle=None - Значение с типом WinRect, содержащее размеры клиентской области окна.
            * State=None - Значение с типом WinState, содержащее состояние окна.
            * StringID=None - только чтение, строка, суммирующая все признаки окна в формате AutoIt (с использованием
            кв. скобок, подронее см. в помощи  AutoIt),
                может быть использована для передачи функциям AutoIt.
    """

    Header = None
    Class = None
    Handle = None
    Rectangle = None
    ClientRectangle = None
    State = None
    StringID = None
    Text = ''

    #-------------------------------------------------------------------------------

    def __init__(self, Header, Class=None, Handle=None, REtitle=False, REclass=False, Text=''):
        #self.SetParams(Header, Class, Handle)
        self.__HeaderPrefix__ = 'REGEXPTITLE' if REtitle else 'TITLE'
        self.__ClassPrefix__ = 'REGEXPCLASS' if REclass else 'CLASS'
        self.Header = Header
        self.Class = Class
        self.Handle = Handle
        self.Rectangle = WinRect(0, 0, 0, 0)
        self.ClientRectangle = WinRect(0, 0, 0, 0)
        self.State = WinState(0)
        self.StringID = self.__FormStringID__(Header, Class, Handle)
        self.Text = Text

    #-------------------------------------------------------------------------------

    def __setattr__(self, Name, Value):
        if Name == 'StringID':
            super().__setattr__(Name, self.__FormStringID__(self.Header, self.Class, self.Handle))
        elif Name == 'Class' or Name == 'Header' or Name == 'Handle':
            super().__setattr__(Name, Value)
            super().__setattr__('StringID', self.__FormStringID__(self.Header, self.Class, self.Handle))
        else:
            super().__setattr__(Name, Value)

    #-------------------------------------------------------------------------------
    def SetParams(self, Header, Class, Handle):
        self.Header = Header
        self.Class = Class
        self.Handle = Handle
        self.Rectangle = WinRect(0, 0, 0, 0)
        self.ClientRectangle = WinRect(0, 0, 0, 0)
        self.State = WinState(0)
        self.StringID = self.__FormStringID__(Header, Class, Handle)

    #-------------------------------------------------------------------------------

    def __FormStringID__(self, Header, Class, Handle):
        Res = '['
        if Handle and Handle != '':
            Res += 'HANDLE:{};'.format(Handle)
        if Header and Header != '':
            Res += '{}:{};'.format(self.__HeaderPrefix__, Header)
        if Class and Class != '':
            Res += '{}:{};'.format(self.__ClassPrefix__, Class)
        Res += ']'
        return Res


#-------------------------------------------------------------------------------

class ControlParams:
    """
        Класс для хранения параметров контролов (элементов окна).

        Параметры конструктора:
            * Class=None - класс котрола. Либо строка с параметрами контрола в квадратных скобках
            (формат см. в помощи AutoIt)
            * Instance=None - номер экземпляра (Instance) контрола.
            * Name=None - Имя контрола.
            * ID=None - Идентификатор контрола.
            * Text='' - Текст, содержащийся в контроле, если он есть.
            * Handle=None - Handle контрола.
            * Rectangle=None - Объект с типом WinRect, содержащий координаты области контрола внутри окна.
        Свойства:
            * Class=None - класс котрола.
            * Instance=None - номер экземпляра (Instance) контрола.
            * Name=None - Имя контрола.
            * ID=None - Идентификатор контрола.
            * Text='' - Текст, содержащийся в контроле, если он есть.
            * Handle=None - Handle контрола.
            * Rectangle=None - Объект с типом WinRect, содержащий координаты области контрола внутри окна.
            * StringID=None - строка, суммирующая все признаки контрола в формате AutoIt (с использованием кв. скобок,
            подронее см. в помощи  AutoIt),
                может быть использована для передачи функциям AutoIt.

    """

    Class = None
    Instance = None
    Name = None
    ID = None
    Text = ''
    Handle = None
    Rectangle = None
    StringID = None
    __Complementary__ = {
        'CLASS': 'Class',
        'INSTANCE': 'Instance',
        'NAME': 'Name',
        'ID': 'ID',
        'TEXT': 'Text',
        'HANDLE': 'Handle'
    }

    #-------------------------------------------------------------------------------

    def __init__(self, Class, Instance=1, Name=None, ID=None, Text='', Handle=None, Rectangle=None):
        if isinstance(Class, str):
            if Class.find('[') == 0 and Class.find(']') == len(Class) - 1:
                self.SetParamsFromString(Class, Rectangle)
            else:
                self.SetParams(Class, Instance, Name, ID, Text, Handle, Rectangle)
        else:
            raise ValueError('Неверный параметр класса: "{}"'.format(Class))

    #-------------------------------------------------------------------------------

    def SetParams(self, Class, Instance, Name, ID, Text, Handle, Rectangle):
        self.Class = Class
        self.Instance = Instance
        self.Name = Name
        self.ID = ID
        self.Text = Text
        self.Handle = Handle
        self.StringID = self.__FormStringID__(Class, Instance, Name, ID, Text, Handle)
        self.Rectangle = Rectangle

    #-------------------------------------------------------------------------------

    def SetParamsFromString(self, ControlString, Rectangle):
        self.StringID = ControlString  # str(ControlString).upper()
        InDict = self.__TakeFromString__(self.StringID)
        for Param, Value in InDict.items():
            self.__dict__[self.__Complementary__[Param]] = Value
        self.Rectangle = Rectangle

    #-------------------------------------------------------------------------------

    def __FormStringID__(self, Class, Instance, Name, ID, Text, Handle):
        Res = '['
        Res += 'CLASS:{};INSTANCE:{};'.format(Class, Instance)
        if Name:
            Res += 'NAME:{};'.format(Name)
        if ID:
            Res += 'ID:{};'.format(ID)
        if Text:
            Res += 'TEXT:{};'.format(Text)
        if Handle:
            Res += 'HANDLE:{};'.format(Handle)
        Res += ']'
        return Res

    #-------------------------------------------------------------------------------

    def __TakeFromString__(self, ControlString):
        Res = None
        tmpStr = ControlString.strip('[]')
        ParList = list(T.strip() for T in tmpStr.split(';'))
        if len(ParList) > 0:
            Res = dict()
            for Record in ParList:
                RecSplit = list(R.strip() for R in Record.split(':'))
                ParName = RecSplit[0].upper()
                Res[ParName] = int(RecSplit[1]) if ParName == 'INSTANCE' else RecSplit[1]
        return Res


#-------------------------------------------------------------------------------
# Декоратор для стандартного вызова с разбором параметров на предмет наличия None-значений.

def AutoItCall(Mode):
    def MainDecorator(AutoFunc):

        @wraps(AutoFunc)
        def wrapper(*arg, **kwarg):
            Res = None
            ModeString = Mode.upper()
            if not None in arg and not None in kwarg.values():
                Res = AutoFunc(*arg, **kwarg)
                if ModeString == 'VALUE':
                    return Res.value
                elif ModeString == 'TRUE-FALSE':
                    if Res > 0:
                        return True
                    else:
                        return False
                elif ModeString == 'STRING-BUF':
                    if Res.value != '':
                        return Res.value
                    else:
                        return None
                elif ModeString == 'RAW':
                    return Res
            else:
                print('Неверные значения аргументов функции "{}", функция не выполнена!'.format(AutoFunc.__name__))

        return wrapper

    return MainDecorator


#-------------------------------------------------------------------------------
class AutoItX:
    """
        Класс-обертка для доступа к функциям AutoItX3.DLL

        Параметры конструктора:

        * PathToDLL=None - Путь к AutoItX3.DLL, если не задан, то AutoItX3.DLL ищется в той же папке, где лежит
        данный модуль.
    """

    __AutoItDLL__ = None
    __Mnemonic__ = 'AutoItX'
    __x64__ = False

    #-------------------------------------------------------------------------------

    def __init__(self, PathToDLL=None):

        #Словарь с описанием параметров функций AutoItX3.DLL
        AutoDLLdict = {
            'AU3_error': {
                'ReturnType': 'c_long',
                'ArgTypes': '()'
            },
            'AU3_MouseClick': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_long, c_long, c_long, c_long)'
            },
            'AU3_MouseClickDrag': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_long, c_long, c_long, c_long, c_long)'
            },
            'AU3_WinGetHandle': {
                'ReturnType': 'HWND',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinGetHandleAsText': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_WinExists': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinGetState': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinGetPos': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, POINTER(c_int * 4))'
            },
            'AU3_WinGetClientSize': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, POINTER(c_int * 4))'
            },
            'AU3_WinActivate': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinActive': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinClose': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinGetCaretPos': {
                'ReturnType': 'c_int',
                'ArgTypes': '(POINTER(c_int * 2),)'
            },
            'AU3_WinGetClassList': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_WinGetProcess': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_WinWait': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_WinWaitActive': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_WinWaitClose': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_WinWaitNotActive': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_WinGetText': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_WinGetTitle': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_WinKill': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p)'
            },
            'AU3_WinMenuSelectItem': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_WinMinimizeAll': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '()'
            },
            'AU3_WinMinimizeAllUndo': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '()'
            },
            'AU3_WinMove': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long, c_long, c_long, c_long)'
            },
            'AU3_WinSetOnTop': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_WinSetState': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_WinSetTitle': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_WinSetTrans': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_ControlClick': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_long, c_long, c_long)'
            },
            'AU3_ControlGetHandle': {
                'ReturnType': 'HWND',
                'ArgTypes': '(HWND, c_wchar_p)'
            },
            'AU3_ControlGetHandleAsText': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_ControlGetText': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_ControlGetTextByHandle': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(HWND, HWND, c_wchar_p, c_int)'
            },
            'AU3_ControlCommand': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_Send': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_long)'
            },
            'AU3_ControlGetPos': {
                'ReturnType': 'c_int',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, POINTER(c_int * 4))'
            },
            'AU3_ControlGetPosByHandle': {
                'ReturnType': 'c_int',
                'ArgTypes': '(HWND, HWND, POINTER(c_int * 4))'
            },
            'AU3_ControlListView': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_ControlDisable': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_ControlEnable': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_ControlFocus': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_ControlGetFocus': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_ControlGetFocusByHandle': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(HWND, c_wchar_p, c_int)'
            },
            'AU3_ControlHide': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_ControlShow': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_ControlMove': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_long, c_long, c_long, c_long)'
            },
            'AU3_ControlSend': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_long)'
            },
            'AU3_ControlSetText': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p)'
            },
            'AU3_ControlTreeView': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_wchar_p, c_int)'
            },
            'AU3_StatusbarGetText': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_wchar_p, c_long, c_wchar_p, c_int)'
            },
            'AU3_MouseDown': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p,)'
            },
            'AU3_MouseUp': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p,)'
            },
            'AU3_MouseMove': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_long, c_long, c_long)'
            },
            'AU3_MouseWheel': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_long)'
            },
            'AU3_MouseGetCursor': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '()'
            },
            'AU3_MouseGetPos': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(POINTER(c_int * 2),)'
            },
            'AU3_PixelChecksum': {
                'ReturnType': 'c_ulong',
                'ArgTypes': '(c_long, c_long, c_long, c_long, c_long)'
            },
            'AU3_PixelGetColor': {
                'ReturnType': 'c_long',
                'ArgTypes': '(c_long, c_long)'
            },
            'AU3_PixelSearch': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_long, c_long, c_long, c_long, c_long, c_long, c_long, PixelSearchRetTypeP)'
            },
            'AU3_ClipGet': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p, c_int)'
            },
            'AU3_ClipPut': {
                'ReturnType': 'c_void_p',
                'ArgTypes': '(c_wchar_p,)'
            },
            'AU3_IsAdmin': {
                'ReturnType': 'c_long',
                'ArgTypes': '()'
            },
        }
        #Ищем и грузим AutoItX3.DLL
        if sysMaxSize > 2 ** 32:
            self.__x64__ = True
            dllKa = 'side_libs\\AutoItX3_x64.dll'
        else:
            dllKa = 'side_libs\\AutoItX3.dll'
        tmpPath = PathToDLL if PathToDLL is not None else os.path.join(os.path.split(globals()['__file__'])[0], dllKa)
        self.__AutoItDLL__ = CustomWinDLL(AutoDLLdict, tmpPath)
        if not self.__AutoItDLL__:
            raise RuntimeError('Невозможно загрузить библиотеку AutoIt!')
        #Определяем метод Error, возврщающий признак ошибки из AutoItX3.dll
        self.Error = self.__AutoItDLL__.AU3_error
        #Пробрасываем MessageBoxW из User32.dll
        self.__MsgBox__ = windll.user32.MessageBoxW
        self.__MsgBox__.restype = c_int
        self.__MsgBox__.argtypes = (HWND, c_wchar_p, c_wchar_p, c_uint)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def MouseClick(self, X, Y, NumClicks=1, Button='left', Speed=-1):
        """
            Метод клика мышью по точке на экране.

            * X - координата по горизонтали.
            * Y - координата по вертикали.
            * NumClicks=1 - количество нажатий.
            * Button='left' - какой кнопкой нажимать (может быть "", "left", "middle", "right", "primary", "main",
            "secondary", "menu", подробнее - см. помощь AutoIt).
            * Speed=-1 - скорость нажатия, от 0 до 100, чем больше, тем медленнее, по умолчанию -1, что дает 10.

            Возвращает True в случае успеха, False в случае неудачи.
        """
        tmp = str(Button).lower()
        RealButton = tmp if tmp in ('left', 'right') else 'left'
        Res = self.__AutoItDLL__.AU3_MouseClick(RealButton, X, Y, NumClicks, Speed)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def MouseClickDrag(self, X, Y, NewX, NewY, Button='left', Speed=-1):
        """
            Перетаскивание мышью.

            * X - координата начала перетаскивания по горизонтали.
            * Y - координата начала перетаскивания по вертикали.
            * NewX - координата окончания перетаскивания по горизонтали.
            * NewY - координата окончания перетаскивания по вертикали.
            * Button='left' - какой кнопкой тащить (может быть "", "left", "middle", "right", "primary", "main",
            "secondary", "menu", подробнее - см. помощь AutoIt).
            * Speed=-1 - скорость нажатия, от 0 до 100, чем больше, тем медленнее, по умолчанию -1, что дает 10.

            Возвращает True в случае успеха, False в случае неудачи.
        """
        tmp = str(Button).lower()
        RealButton = tmp if tmp in ('left', 'right') else 'left'
        Res = self.__AutoItDLL__.AU3_MouseClickDrag(RealButton, X, Y, NewX, NewY, Speed)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def MouseDown(self, Button='left'):
        """
            Нажать и удерживать кнопку мыши.

            * Button='left' - какую кнопку нажать (может быть "", "left", "middle", "right", "primary", "main",
            "secondary", "menu",
                подробнее - см. помощь AutoIt).

            Возвращает True.
        """
        tmp = str(Button).lower()
        RealButton = tmp if tmp in ('left', 'right') else 'left'
        self.__AutoItDLL__.AU3_MouseDown(RealButton)
        return True

    @AutoItCall('RAW')
    def MouseUp(self, Button='left'):
        """
            Отпустить кнопку мыши.

            * Button='left' - какую кнопку отпустить (может быть "", "left", "middle", "right", "primary", "main",
            "secondary", "menu",
                подробнее - см. помощь AutoIt).

            Возвращает True.
        """
        tmp = str(Button).lower()
        RealButton = tmp if tmp in ('left', 'right') else 'left'
        self.__AutoItDLL__.AU3_MouseUp(RealButton)
        return True

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def MouseMove(self, X, Y, Speed=-1):
        """
            Передвинуть курсор мыши.

            * X - координата по горизонтали.
            * Y - координата по вертикали.
            * Speed=-1 - скорость нажатия, от 0 до 100, чем больше, тем медленнее, по умолчанию -1, что дает 10.

            Возвращает True.
        """
        self.__AutoItDLL__.AU3_MouseMove(X, Y, Speed)
        return True

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def MouseWheel(self, Direction, Clicks=1):
        """
            Прокрутить колесико мыши.

            * Direction - направление прокрутки, может быть 'up' или 'down'
            * Clicks=1 - на какое количество "кликов" прокрутить.

            Возвращает True.
        """
        tmp = str(Direction).lower()
        RealDir = tmp if tmp in ('up', 'down') else 'down'
        self.__AutoItDLL__.AU3_MouseWheel(RealDir, Clicks)
        return True

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def MouseGetCursor(self):
        """
            Определить текущий тип курсора мыши.

            Возвращает строковое название типа курсора.
        """
        return MouseGetCursorValue[self.__AutoItDLL__.AU3_MouseGetCursor()]

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def MouseGetPos(self):
        """
            Определение положения курсора мыши.

            Возвращает объект типа WinPoint с координатами курсора.
        """
        tmpCtypes = c_int * 2
        ttmmpp = tmpCtypes(0, 0)
        self.__AutoItDLL__.AU3_MouseGetPos(pointer(ttmmpp))
        return WinPoint(*list(p for p in ttmmpp))

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetHandle(self, Title, Text=''):
        """
            Получить Handle окна.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку, содержащую Handle окна в шестнадцатиричном виде с префиксом,например: "0x007F39".
            С помощью лямбды WinHandle результат можно преобразовать в строку заголовка в формате AutoIt:
            WinHandle(AutoItObj.WinGetHandle('Заголовок окна'))
            в результате получим строку вида
            "0x<значение Handle>", которую можно использовать для работы с окнами вместо заголовка.
        """
        bufSize = 19 if self.__x64__ else 11
        tmp = create_unicode_buffer(bufSize)
        self.__AutoItDLL__.AU3_WinGetHandleAsText(Title, Text, tmp, bufSize)
        Res = tmp.value if tmp.value != '' else None
        #Res = '0x{}'.format(tmp.value) if tmp.value != '' else None
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetHandleInt(self, Title, Text=''):
        """
            Получить Handle окна.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает числовое значение Handle окна
        """
        Res = self.__AutoItDLL__.AU3_WinGetHandle(Title, Text)
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinExists(self, Title, Text=''):
        """
            Определить существует ли окно.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True, если окно существует, False, если нет.
        """
        return self.__AutoItDLL__.AU3_WinExists(Title, Text)

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetState(self, Title, Text=''):
        """
            Получить состояние окна в числовом виде.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Интерпретировать можно с помошью класса WinState (см. его докстринг)
            В случае неудачи возвращает 0.
        """
        return self.__AutoItDLL__.AU3_WinGetState(Title, Text)

        #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetPos(self, Title, Text=''):
        """
            Получить координаты квадрата, который занят окном на экране.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает объект типа WinRect, содержащий координаты верхнего левого угла окна, его ширину и высоту,
            возвращает None в случае неудачи.
        """
        tmpCtypes = c_int * 4
        ttmmpp = tmpCtypes(0, 0, 0, 0)
        self.__AutoItDLL__.AU3_WinGetPos(Title, Text, pointer(ttmmpp))
        if self.Error() == 0:
            Res = WinRect(*list(p for p in ttmmpp))
        else:
            Res = None

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetClientRect(self, Title, Text=''):
        """
            Получить координаты квадрата, который занимает клиентская область окна на экране.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает объект типа WinRect, содержащий координаты верхнего левого угла, ширину и высоту.
        """
        tmpCtypes = c_int * 4
        ttmmpp = tmpCtypes(0, 0, 0, 0)
        #pTmp = pointer(ttmmpp)
        self.__AutoItDLL__.AU3_WinGetClientSize(Title, Text, pointer(ttmmpp))
        cwa = list(p for p in ttmmpp)
        wra = self.WinGetPos(Title, Text)
        if wra:
            ClientWidth = cwa[2]  # if cwa[2] < wra[2] else wra[2]
            ClientHeight = cwa[3]  # if cwa[3] < wra[3] else wra[3]
            BorderWidth = (wra[2] - wra[0] - ClientWidth) // 2
            ClientX = wra[0] + BorderWidth
            ClientY = wra[3]-cwa[3]-BorderWidth #(wra[3] - wra[1] - ClientHeight) // 2

            return WinRect(ClientX, ClientY, ClientWidth, ClientHeight)
        else:
            return None

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinActivate(self, Title, Text=''):
        """
            Сделать окно активным.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True.
        """

        return self.__AutoItDLL__.AU3_WinActivate(Title, Text)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinActive(self, Title, Text=''):
        """
            Определить активно ли окно.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            В случае успеха возвращает строку, содержащую Handle окна в шестнадцатиричном виде,
            иначе None.

        """
        #tmp = self.__AutoItDLL__.AU3_WinActive(Title, Text)
        #Res = str(tmp) if tmp != 0 else None
        return self.__AutoItDLL__.AU3_WinActive(Title, Text)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinClose(self, Title, Text=''):
        """
            Закрыть окно.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха, False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinClose(Title, Text)

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetCaretPos(self):

        """
            Определить положение текстового курсора (каретки) в окне.

            Возвращает объект типа WinPoint с относительными координатами курсора в окне.
            В случает неудачи метод Error() вернет 1.
        """
        tmpCtypes = c_int * 2
        self.__AutoItDLL__.AU3_WinGetCaretPos(pointer(tmpCtypes))
        return WinPoint(*list(p for p in tmpCtypes))
        #return WinPoint(self.__AutoItDLL__.AU3_WinGetCaretPosX(), self.__AutoItDLL__.AU3_WinGetCaretPosY())

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def WinGetClassList(self, Title, Text=''):
        """
            Получить список классов окна.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает список всех классов окна и его элементов в виде строки.
            В случае неудачи вернет None, метод Error() вернет 1.

        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_WinGetClassList(Title, Text, Res, 65535)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def WinGetProcess(self, Title, Text=''):
        """
            Получить PID процесса окна.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку с PID процесса окна в десятиричном формате.
            В случае неудачи вернет None.
        """
        Res = create_unicode_buffer(9)
        self.__AutoItDLL__.AU3_WinGetProcess(Title, Text, Res, 9)

        if len(Res.value) > 0:
            return int(Res.value)
        else:
            return None

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def WinGetText(self, Title, Text=''):
        """
            Получить текст окна.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает текст окна в виде строки,
            в случае неудачи - None.
        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_WinGetText(Title, Text, Res, 65535)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def WinGetTitle(self, Title, Text=''):
        """
            Получить заголовок окна.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает заголовок окна,
            в случае неудачи - None.
        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_WinGetTitle(Title, Text, Res, 65535)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinKill(self, Title, Text=''):
        """
            Принудительно закрыть окно.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinKill(Title, Text)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinWait(self, Title, Timeout, Text=''):
        """
            Ожидание открытия окна.

            * Title - Заголовок окна в формате AutoIt.
            * Timeout - время ожидания в секундах
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinWait(Title, Text, Timeout)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinWaitActive(self, Title, Timeout, Text=''):
        """
            Ожидание активного (ACTIVE) состояния окна.

            * Title - Заголовок окна в формате AutoIt.
            * Timeout - время ожидания в секундах
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinWaitActive(Title, Text, Timeout)

    #-------------------------------------------------------------------------------

    def WinWaitActivePing(self, Title, Timeout, Text=''):
        isActive = self.__AutoItDLL__.AU3_WinActivate(Title, Text)
        #isActive = self.WinActive(Title, Text)
        #i = Timeout
        if not isActive:
            for i in range(Timeout+1,0,-1):
                sleep(1)
                isActive = self.__AutoItDLL__.AU3_WinActivate(Title, Text)
                #i -= 1
                #isActive = self.WinActive(Title, Text)
                if isActive:
                    break
        return isActive

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinWaitClose(self, Title, Timeout, Text=''):
        """
            Ожидание закрытия окна.

            * Title - Заголовок окна в формате AutoIt.
            * Timeout - время ожидания в секундах
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinWaitClose(Title, Text, Timeout)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinWaitNotActive(self, Title, Timeout, Text=''):
        """
            Ожидание неактивного состояния окна.

            * Title - Заголовок окна в формате AutoIt.
            * Timeout - время ожидания в секундах
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinWaitNotActive(Title, Text, Timeout)

    #-------------------------------------------------------------------------------

    def WinWaitState(self, Title, State, Timeout, Interval=0.25, Text=''):
        """
            Ожидание перехода окна в состояние, заданное параметром State.
            * Title - Заголовок окна в формате AutoIt.
            * State - Состояние окна, которого необходимо дождаться. Задается числом (подробнее см. помощь Auto It по
            функции WinGetState),
                либо строкой с перечислением признаков, например: "ENABLED, VISIBLE, ACTIVE".
            * Timeout - Время ожидания в секундах, вещественное число для представления долей секунд.
            * Interval=0.25 - Интервал проверки состояния.
            * Text='' - Текст, содержащийся в окне.

            Возвращает время, прошедшее с начала ожидания в случае успеха,
             0 - если не удалось дождаться нужного состояния за заданное время,
            -1 - если окно не было обнаружено.
        """
        tmpState = WinState(State).StateNum
        tmpTimeout = Timeout if Timeout > 0 else 10
        Res = 0
        if self.WinExists(Title, Text):
            CurState = self.WinGetState(Title, Text)
            Delta = 0
            Expired = False
            Start = perf_counter()
            while CurState != tmpState:
                sleep(Interval)
                if self.WinExists(Title, Text):
                    CurState = self.WinGetState(Title, Text)
                else:
                    Res = -1
                    break
                Delta = perf_counter() - Start
                if Delta >= tmpTimeout:
                    Expired = True
                    break
            if not Expired:
                Res = Delta
        else:
            Res = -1

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinMenuSelectItem(self, Title, Item1, Item2='', Item3='', Item4='', Item5='', Item6='', Item7='', Item8='',
                          Text=''):
        """
            Вызов элементов меню окна последовательно по уровням вложенности, вплоть до восьми.
            Работает только со стандартным меню окна, которое сейчас редко используется.

            * Title - Заголовок окна в формате AutoIt.
            * Item1 - имя первого в последовательности вызова элемента меню.
            * Item2='' - имя второго в последовательности вызова элемента меню.
            * Item3='' - имя третьего в последовательности вызова элемента меню.
            * Item4='' - имя четвертого в последовательности вызова элемента меню.
            * Item5='' - имя пятого в последовательности вызова элемента меню.
            * Item6='' - имя шестого в последовательности вызова элемента меню.
            * Item7='' - имя седьмого в последовательности вызова элемента меню.
            * Item8='' - имя восьмого в последовательности вызова элемента меню.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        Res = self.__AutoItDLL__.AU3_WinMenuSelectItem(Title, Text, Item1, Item2, Item3, Item4, Item5, Item6, Item7,
                                                       Item8)
        return Res

    #-------------------------------------------------------------------------------

    def WinMinimizeAll(self):
        """
            Свернуть все окна.

            Возвращает True.
        """
        self.__AutoItDLL__.AU3_WinMinimizeAll()
        return True

    def WinMinimizeAllUndo(self):
        """
            Отменить сворачивание всех окон.

            Возвращает True.
        """
        self.__AutoItDLL__.AU3_WinMinimizeAllUndo()
        return True

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinMove(self, Title, X, Y, Width=-1, Height=-1, Text=''):

        """
            Передвинуть окно.

            * Title - Заголовок окна в формате AutoIt.
            * X - координата нового положения верхнего правого угла окна по горизонтали.
            * Y - координата нового положения верхнего правого угла окна по вертикали.
            * Width=-1 - Новая ширина окна.
            * Height=-1 - Новая высота окна.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinMove(Title, Text, X, Y, Width, Height)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinSetOnTop(self, Title, Flag=1, Text=''):
        """
            Изменить признак окна "поверх всех".

            * Title - Заголовок окна в формате AutoIt.
            * Flag=1 - значение признака "поверх всех", 0 - не установлен, 1 - установлен.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinSetOnTop(Title, Text, Flag)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinSetState(self, Title, State, Text=''):
        """
            Изменить состояние окна.

            * Title - Заголовок окна в формате AutoIt.
            * State - Новое значение состояния окна. Формируется при помощи именованного массива SW
                побитовым "или":
                SW.ENABLE|SW.MAXIMIZE
                подробно о значениях см. помощь AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinSetState(Title, Text, State)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinSetTitle(self, Title, NewTitle, Text=''):
        """
            Изменить заголовок окна.

            * Title - Заголовок окна в формате AutoIt.
            * NewTitle - новое значение заголовка окна.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.

        """
        return self.__AutoItDLL__.AU3_WinSetTitle(Title, Text, NewTitle)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def WinSetTrans(self, Title, TransVal, Text=''):
        """
            Изменить степень прозрачности окна.

            * Title - Заголовок окна в формате AutoIt.
            * TransVal - новое значение прозрачности. Шкала от 0 до 255, прозрачно -> непрозрачно.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_WinSetTrans(Title, Text, TransVal)

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def ControlGetHandle(self, Title, Control, Text=''):
        """
            Получить Handle контрола в окне.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Строковой идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку, содержащую Handle контрола в шестнацатиричном формате,
            в случае неудачи None.
        """
        #Res = create_unicode_buffer(255)
        bufSize = 19 if self.__x64__ else 11
        tmp = create_unicode_buffer(bufSize)
        self.__AutoItDLL__.AU3_ControlGetHandleAsText(Title, Text, Control, tmp, bufSize)
        Res = tmp.value if tmp.value != '' else None
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def ControlGetHandleInt(self, Handle, Control):
        """
            Получить Handle контрола в окне.

            * Handle - Числовое значение Handle окна с контролом.
            * Control - Строковой идентификатор контрола в формате AutoIt.

            Возвращает числовое значение Handle контрола,
            в случае неудачи - None.
        """
        Res = self.__AutoItDLL__.AU3_ControlGetHandle(Handle, Control)
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def ControlGetText(self, Title, Control, Text=''):
        """
            Получить текст из контрола в окне.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку, содержащую текст из контрола,
            в случае неудачи - None.
        """
        Res = create_unicode_buffer(4095)
        self.__AutoItDLL__.AU3_ControlGetText(Title, Text, Control, Res, 4095)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def ControlGetTextByHandle(self, WinHandle, ControlHandle):
        """
            Получить текст из контрола в окне.

            * WinHandle - int значение Handle окна.
            * ControlHandle - int значение Handle контрола.

            Возвращает строку, содержащую текст из контрола,
            в случае неудачи - None.
        """
        Res = create_unicode_buffer(4095)
        self.__AutoItDLL__.AU3_ControlGetTextByHandle(WinHandle, ControlHandle, Res, 4095)

        return Res

    #-------------------------------------------------------------------------------
    @AutoItCall('STRING-BUF')
    def ControlCommand(self, Title, Control, Command, ExtraData='', Text=''):
        """
            Отправить команду контролу в окне.
            Работает в основном со стандартными контролами типа "ToolbarWindow32", "ComboBox","ListBox" и т.п.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Command - Строка с командой (подробнее - см. помощь AutoIt)
            * ExtraData='' - Строка с дополнительными параметрами для команды (подробнее - см. помощь AutoIt).
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку с результатом выполнения команды, содержимое различается, в зависимости от команды.
            В случае ошибок метод Error() вернет 1.
        """
        Res = create_unicode_buffer(255)
        self.__AutoItDLL__.AU3_ControlCommand(Title, Text, Control, Command, ExtraData, Res, 255)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def ControlGetPos(self, Title, Control, Text=''):
        """
            Получить парамтры области контрола в окне.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает объект WinRect с параметрам области котрола.
            В случае ошибок вернет None.
        """
        #tmp = []
        tmpCtypes = c_int * 4
        ttmmpp = tmpCtypes(0, 0, 0, 0)
        self.__AutoItDLL__.AU3_ControlGetPos(Title, Text, Control, pointer(ttmmpp))
        if self.Error() == 0:
            #for val in ttmmpp:
            #    tmp.append(val)
            Res = WinRect(*list(v for v in ttmmpp))
        else:
            Res = None

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def ControlGetPosByHandle(self, WinHandle, ControlHandle):
        """
            Получить парамтры области контрола в окне.

            * WinHandle - int значение Handle окна.
            * ControlHandle - int значение Handle контрола.

            Возвращает объект WinRect с параметрам области котрола.
            В случае ошибок вернет None.
        """
        #tmp = []
        tmpCtypes = c_int * 4
        ttmmpp = tmpCtypes(0, 0, 0, 0)
        self.__AutoItDLL__.AU3_ControlGetPosByHandle(WinHandle, ControlHandle, pointer(ttmmpp))
        if self.Error() == 0:
            #for val in ttmmpp:
            #    tmp.append(val)
            Res = WinRect(*list(v for v in ttmmpp))
        else:
            Res = None

        return Res

    #-------------------------------------------------------------------------------
    @AutoItCall('RAW')
    def ControlGetParams(self, Title, Control, Text=''):
        """
            Определить параметры котрола.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает объект типа ControlParams с параметрами контрола,
            в случае неудачи - None
        """
        ContHandle = self.ControlGetHandle(Title, Control, Text)
        if ContHandle:
            Res = ControlParams(Control)
            Res.Handle = ContHandle
            if not Res.Rectangle:
                Res.Rectangle = self.ControlGetPos(Title, Control, Text)
        else:
            Res = None

        return Res

        #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlMouseClick(self, Title, Control, X, Y, NumClicks=1, Button='left', Speed=-1, Text=''):
        """
            Нажать мышью на точку в области контрола.
            Моя замена функции ControlClick из AutoIt, работает за счет обычного MouseClick.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * X - относительная координата точки по горизонтали в области контрола.
            * Y - относительная координата точки по вертикали в области контрола.
            * NumClicks=1 - количество нажатий.
            * Button='left' - какой кнопкой нажимать (может быть "", "left", "middle", "right", "primary", "main",
            "secondary", "menu", подробнее - см. помощь AutoIt).
            * Speed=-1 - скорость нажатия, от 0 до 100, чем больше, тем медленнее, по умолчанию -1, что дает 10.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        Res = None
        WinClientRectangle = self.WinGetClientRect(Title, Text)
        #ControlX = self.__AutoItDLL__.AU3_ControlGetPosX(Title, Text, Control)
        #ControlY = self.__AutoItDLL__.AU3_ControlGetPosY(Title, Text, Control)
        ControlPoint = self.ControlGetPos(Title, Control, Text)
        if WinClientRectangle and ControlPoint:
            Res = self.MouseClick(
                WinClientRectangle.X + ControlPoint.X + X,
                WinClientRectangle.Y + ControlPoint.Y + Y,
                NumClicks,
                Button,
                Speed
            )

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlClick(self, Title, Control, X, Y, NumClicks=1, Button='left', Text=''):
        """
            Нажать мышью на точку в области контрола.
            Проброс стандартной функции из AutoIt.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * X - относительная координата точки по горизонтали в области контрола.
            * Y - относительная координата точки по вертикали в области контрола.
            * NumClicks=1 - количество нажатий.
            * Button='left' - какой кнопкой нажимать (может быть "", "left", "middle", "right", "primary", "main",
            "secondary", "menu", подробнее - см. помощь AutoIt).
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlClick(Title, Text, Control, Button, NumClicks, X, Y)

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def ControlListView(self, Title, Control, Command, Extra1='', Extra2='', Text=''):
        """
            Послать команду котролу с классом ListView32.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Command - Строка с командой (подробнее - см. помощь AutoIt)
            * Extra1='' - Строка с дополнительными параметрами для команды (подробнее - см. помощь AutoIt).
            * Extra2='' - Строка с дополнительными параметрами для команды (подробнее - см. помощь AutoIt).
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку с результатом выполнения команды, содержимое различается, в зависимости от команды.
            В случае ошибок метод Error() вернет 1.
        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_ControlListView(Title, Text, Control, Command, Extra1, Extra2, Res, 65535)
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlDisable(self, Title, Control, Text=''):
        """
            Выключить контрол.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlDisable(Title, Text, Control)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlEnable(self, Title, Control, Text=''):
        """
            Включить контрол.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlEnable(Title, Text, Control)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlFocus(self, Title, Control, Text=''):
        """
            Перевести фокус ввода на контрол.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlFocus(Title, Text, Control)

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def ControlGetFocus(self, Title, Text=''):
        """
            Определить в каком контроле находится фокус ввода.

            * Title - Заголовок окна в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку с именем контрола, в котором находится фокус ввода,
            в случае нейдачи - None.
        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_ControlGetFocus(Title, Text, Res, 65535)
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def ControlGetFocusByHandle(self, WinHandle):
        """
            Определить в каком контроле находится фокус ввода.

            * WinHandle - int значение Handle окна.

            Возвращает строку с именем контрола, в котором находится фокус ввода,
            в случае нейдачи - None.
        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_ControlGetFocusByHandle(WinHandle, Res, 65535)
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlHide(self, Title, Control, Text=''):
        """
            Скрыть контрол.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlHide(Title, Text, Control)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlShow(self, Title, Control, Text=''):
        """
            Показать контрол.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlShow(Title, Text, Control)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlMove(self, Title, Control, X, Y, Width=-1, Height=-1, Text=''):
        """
            Передвинуть контрол.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * X - координата нового положения верхнего правого угла контрола по горизонтали.
            * Y - координата нового положения верхнего правого угла контрола по вертикали.
            * Width=-1 - Новая ширина контрола.
            * Height=-1 - Новая высота контрола.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlMove(Title, Text, Control, X, Y, Width, Height)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlSend(self, Title, Control, String, Flag=0, Text=''):
        """
            Оправить строку в контрол. Работает аналогично стандартной функции Send,
            поддерживает тот же формат для отправки клавиш (см. помощь AutoIt).

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * String - Строка, которая будет передана в контрол.
            * Flag=0 - Флаг интерпретации. Если 0 - будут разобраны спец. последовательности для клавиш, вроде "+" для
            зажатия SHIFT или {клавиша} для отсылки клавиш. Если 1 - строка будет отослана как есть.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlSend(Title, Text, Control, String, Flag)

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ControlSetText(self, Title, Control, NewText, Text=''):
        """
            Изменить текст в контроле.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * NewText - Строка с новым текстом.
            * Text='' - Текст, содержащийся в окне.

            Возвращает True в случае успеха,
            False в случае неудачи.
        """
        return self.__AutoItDLL__.AU3_ControlSetText(Title, Text, Control, NewText)

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def ControlTreeView(self, Title, Control, Command, Extra1='', Extra2='', Text=''):
        """
            Послать команду котролу с классом TreeView32.

            * Title - Заголовок окна в формате AutoIt.
            * Control - Идентификатор контрола в формате AutoIt.
            * Command - Строка с командой (подробнее - см. помощь AutoIt)
            * Extra1='' - Строка с дополнительными параметрами для команды (подробнее - см. помощь AutoIt).
            * Extra2='' - Строка с дополнительными параметрами для команды (подробнее - см. помощь AutoIt).
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку с результатом выполнения команды, содержимое различается, в зависимости от команды.
            В случае ошибок метод Error() вернет 1.
        """
        Res = create_unicode_buffer(65535)
        self.__AutoItDLL__.AU3_ControlTreeView(Title, Text, Control, Command, Extra1, Extra2, Res, 65535)
        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('STRING-BUF')
    def StatusbarGetText(self, Title, Part=1, Text=''):
        """
            Получить текст из строки статуса приложения, работает только в том случае, если это строка состояния с
            классом StatusBar32.

            * Title - Заголовок окна в формате AutoIt.
            * Part - Номер текстового поля, из которого нужно прочесть техт в Statusbar.
            * Text='' - Текст, содержащийся в окне.

            Возвращает строку, содержащую текст из контрола,
            в случае неудачи - None.
        """
        Res = create_unicode_buffer(4095)
        self.__AutoItDLL__.AU3_StatusbarGetText(Title, Text, Part, Res, 4095)

        return Res

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def Send(self, KeyString, NumSends=1, Flag=0):
        """
            Ввод с клавиатуры.

            * KeyString - строка, которую ввести.
            * NumSends=1 - количество повтороав ввода.
            * Flag=0 - Флаг интерпретации. Если 0 - будут рабраны спец. последовательности для клавиш, вроде "+" для
            зажатия SHIFT или {клавиша} для отсылки клавиш. Если 1 - строка будет отослана как есть.

            Возвращает количество отправок строки (обычно оно равно NumSends).
        """
        i=0
        for i in range(1, NumSends + 1):
            self.__AutoItDLL__.AU3_Send(KeyString, Flag)

        return i

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def PixelChecksum(self, Left, Top, Right, Bottom, Step=1):
        """
            Вычислить контрольную сумму области на экране.
            Помогает отслеживать изменения в этой области.
            Работает достаточно медленно, поэтому большие области обсчитывать не рекомендуется.

            * Left - координата левого верхнего угла просчитываемой области экрана по горизонтали.
            * Top - координата левого верхнего угла просчитываемой области экрана по вертикали.
            * Right - координата правого нижнего угла просчитываемой области экрана по горизонтали.
            * Bottom - координата правого нижнего угла просчитываемой области экрана по вертикали.
            * Step=1 - шаг в пикселах, позволяет ускорить просчет путем пропуска пикселов, но это может привести к тому,
             что изменения на экране не отразятся в результирующей сумме, если они попадут в пропущенные области.

            Возвращает число - контрольную сумму заданной области экрана,
            в случае неудачи - возвращает 0.
        """
        return self.__AutoItDLL__.AU3_PixelChecksum(Left, Top, Right, Bottom, Step)

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def PixelGetColor(self, X, Y):
        """
            Определить цвет пиксела на экране.

            * X - координата пиксела по горизонтали.
            * Y - координата пиксела по вертикали.

            Возвращает цвет пиксела в виде шестиразрядного шестнадцатиричного числа,
            по два разряда на цвет, формат RGB.
        """
        return self.__AutoItDLL__.AU3_PixelGetColor(X, Y)

    #-------------------------------------------------------------------------------

    @AutoItCall('RAW')
    def PixelSearch(self, Left, Top, Right, Bottom, Col, Var=0, Step=1):
        """
            Поиск пиксела с определенным цветом в заданной области экрана.

            * Left - координата левого верхнего угла просчитываемой области экрана по горизонтали.
            * Top - координата левого верхнего угла просчитываемой области экрана по вертикали.
            * Right - координата правого нижнего угла просчитываемой области экрана по горизонтали.
            * Bottom - координата правого нижнего угла просчитываемой области экрана по вертикали.
            * Col - цвет пиксела в виде шестиразрядного шестнадцатиричного числа, по два разряда на цвет, формат RGB
            * Var=0 - допуск по оттенку цвета при поиске совпадений, от 0 до 255, задает разброс значений, которые
            попадут под критерий поиска по каждому цвету. 0 - абсолютное соответствие, 255 - совпадет любой цвет.
            * Step=1 - шаг в пикселах, позволяет ускорить поиск путем пропуска пикселов.

            Возвращает объект типа WinPoint с координатами пиксела, если он найден
        """
        tmp = PixelSearchRetType(0, 0)
        self.__AutoItDLL__.AU3_PixelSearch(Left, Top, Right, Bottom, Col, Var, Step, byref(tmp))
        return WinPoint(tmp[0], tmp[1])

    #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def ClipPut(self, Text):
        """
            Помещает текст в буфер обмена.

            * Text - строка, которую надо поместить в буфер обмена.

            Возвращает True в случае успеха, False  в случае неудачи.
        """
        tmp = create_unicode_buffer(Text)
        self.__AutoItDLL__.AU3_ClipPut(tmp)
        return self.Error()

    def ClipGet(self):
        """
            Считывает текст из буфера обмена, не более 65535 байт.
            В случае успеха вернет текст, если в буфере обмена был не текст, а что-то другое, или возникли ошибки,
            вернет None.
        """
        tmp = create_unicode_buffer(65536)
        self.__AutoItDLL__.AU3_ClipGet(tmp, 65536)
        Out = self.Error()
        Res = tmp.value if Out == 0 else None
        return Res

        #-------------------------------------------------------------------------------

    @AutoItCall('TRUE-FALSE')
    def IsAdmin(self):
        return self.__AutoItDLL__.AU3_IsAdmin()

    #-------------------------------------------------------------------------------

    def MsgBox(self, Title, Message, Flags=0, WinHandle=None):
        """
            Простой советский MesageBox, релизован напрямую через User32.dll.

            * Title - Заголовок окна.
            * Message - Сообщение в окне.
            * Flags=0 - Число с флагами для регулировки вида окна, кнопок и т.п. (подробнее см. помощь от  Microsoft по
            MessageBox). Соответствуют стандартным по именам, заключены в именованный массив MB_Flags, использовать,
            например, так:
                MB_Flags.MB_ICONWARNING|MB_Flags.MB_OKCANCEL|MB_Flags.MB_SYSTEMMODAL
            * WinHandle=None - Handle родительского окна, которое открыло MessageBox.
        """
        return self.__MsgBox__(WinHandle, Message, Title, Flags)

#-------------------------------------------------------------------------------

#Точка входа

#def main():
#    pass

#-------------------------------------------------------------------------------
#Запуск точки входа
if __name__ == '__main__':
    pass