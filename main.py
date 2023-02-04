
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode
import logging
import requests
import random
import uuid
import time
from collections import defaultdict
import pickle
import os


API_TOKEN = "YOUR_TOKEN"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Initialize bot and dispatcher
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    reception = State()
    generate = State()
    setting = State()
    host = State()
    username = State()
    password = State()
    url = State()
    url_value = State()
    default = State()
    configurable = State()
    choose_url = State()
    max_traffic = State()
    device_limit = State()
    expire_time = State()


class Admin():
    def __init__(self, id):
        self.id = id
        self.tel_username = ""
        self.host = ""
        self.username = ""
        self.password = ""
        self.url = {}
        self.cookie = ""
        self.remark = ""
        self.port = ""
        self.id_user = ""
        self.max_traffic = 0
        self.device_limit = 0
        self.expire_time = 0


admin_dict = defaultdict(int)

start_keyboard_markup = types.ReplyKeyboardMarkup(
    row_width=2, resize_keyboard=True)
btns_text = ('🔗 Generate', '⚙️ Settings')
start_keyboard_markup.row(*(types.KeyboardButton(text)
                            for text in btns_text))

generate_keyboard_markup = types.ReplyKeyboardMarkup(
    row_width=3, resize_keyboard=True)
btns_text_row = ('Defualt', 'Configurable')
generate_keyboard_markup.row(
    *(types.KeyboardButton(text) for text in btns_text_row))
generate_keyboard_markup.add('🏠 Home')

setting_keyboard_markup = types.ReplyKeyboardMarkup(
    row_width=3, resize_keyboard=True)
btns_text_row1 = ('📤 Panel Host', '👤 Username', '🔑 Password',)
btns_text_row2 = ('➕ Add URL', '🔓 Login', 'ℹ️ Info')

setting_keyboard_markup.row(
    *(types.KeyboardButton(text) for text in btns_text_row1))
setting_keyboard_markup.row(
    *(types.KeyboardButton(text) for text in btns_text_row2))
setting_keyboard_markup.add('🏠 Home')

back_keyboard_markup = types.ReplyKeyboardMarkup(
    row_width=3, resize_keyboard=True)
back_keyboard_markup.add('Back 🔙')


def load_db():

    global admin_dict
    if os.path.exists('db') and os.stat('db').st_size != 0:
        file = open('db', 'rb')
        admin_dict = pickle.load(file)
        file.close()


def update_db():

    file = open('db', 'wb')
    pickle.dump(admin_dict, file)
    file.close()


def request_link(host, remark, cookie, max_traffic=30, device_limit=2, expire_time=30):
    list_response = requests.post(f'{host}/xui/inbound/list', headers={
        "Cookie": cookie
    })
    if list_response.status_code == 200 and list_response.json()['success']:
        users_list = list_response.json()['obj']
        if len(users_list) > 0:
            last_id = users_list[-1]['id']
        else:
            last_id = 0
    else:
        print('error occurred on getting list of users!', list_response.text)
        raise Exception(list_response.text)

    port = random.randint(10000, 2 ** 16)
    user_id = uuid.uuid1()

    body = {
        "id": last_id + 1,
        "up": 0,
        "down": 0,
        "total": max_traffic * (2 ** 30),
        "remark": remark,
        "enable": True,
        "expiryTime": int(time.time() * 1000) + expire_time * 24 * 60 * 60 * 1000,
        "autoreset": True,
        "ipalert": False,
        "iplimit": device_limit,
        "listen": "",
        "port": port,
        "protocol": "vless",
        "settings": f'{{"clients": [{{"id": "{user_id}", "email": "{remark}@xray.com", "flow": ""}}], "decryption": "none", "fallbacks": []}}',
        "streamSettings": f'{{"network": "ws", "security": "none", "wsSettings": {{"path": "/{port}", "headers": {{}}, "acceptProxyProtocol": false}}}}',
        "sniffing": '{"enabled": true, "destOverride": ["http", "tls"]}',
    }
    response = requests.post(f'{host}/xui/inbound/add', json=body, headers={
        'Cookie': cookie
    })
    if response.status_code == 200 and response.json()['success']:
        return user_id, port
    else:
        print('error occurred on adding user!', response.text)
        raise Exception(response.text)


def create_link(user_id, url, port, remark):
    return f"vless://{user_id}@{url}?type=ws&security=tls&path=%2F{port}#{remark}"


@dp.message_handler(commands=['start', 'help'], state='*')
async def start(message: types.Message):

    user_id = message.from_user.id
    # new_admin = Admin(user_id)
    # new_admin.tel_username = message.from_user.username
    # admin_dict[str(user_id)] = new_admin

    load_db()
    if len(admin_dict.keys()) == 0 or not str(user_id) in admin_dict.keys():
        new_admin = Admin(user_id)
        new_admin.tel_username = message.from_user.username
        admin_dict[str(user_id)] = new_admin
        update_db()

    logging.info(
        f"userid : {user_id}, username : {message.from_user.username}  started")

    await Form.reception.set()

    await message.reply(f"Hi {message.from_user.first_name},\nYou can manage your vpn panel")
    await message.answer("Please choose from options below:", reply_markup=start_keyboard_markup)


@ dp.message_handler(Text(equals='🏠 Home', ignore_case=True), state='*')
async def home_handler(message: types.Message, state: FSMContext):

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  pressed Home button")

    await Form.reception.set()
    await message.answer("Please choose from options below:", reply_markup=start_keyboard_markup)


@ dp.message_handler(Text(equals='Back 🔙', ignore_case=True), state='*')
async def back_handler(message: types.Message, state: FSMContext):

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  pressed Bsck button")

    current_state = await state.get_state()
    if current_state is None:
        return

    mystate = str(current_state).split(":")[1]

    if mystate == "host" or mystate == "username" or mystate == "password" or mystate == "url":
        await Form.setting.set()
        await message.answer("Please choose from options below:", reply_markup=setting_keyboard_markup)

    if mystate == "default" or mystate == "configurable" or mystate == "max_traffic" or mystate == "device_limit" or mystate == "expire_time":
        await Form.generate.set()
        await message.answer("Please choose from options below:", reply_markup=generate_keyboard_markup, )


@ dp.message_handler(state=Form.reception)
async def reception(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  choosed {message.text}")

    if message.text == "🔗 Generate":

        if admin_dict[str(user_id)].cookie == "":
            await message.answer('Please first login and then try again:')
            return

        await Form.generate.set()
        await message.answer("Please choose from options below:", reply_markup=generate_keyboard_markup)

    elif message.text == "⚙️ Settings":

        await Form.setting.set()
        await message.answer("Please choose from options below:", reply_markup=setting_keyboard_markup)


@ dp.message_handler(state=Form.setting)
async def setting(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  choosed {message.text}")

    if message.text == "📤 Panel Host":

        # if admin_dict[str(user_id)].host != "":
        #     await message.answer(f'your current host is :\n{admin_dict[str(user_id)].host}')

        await Form.host.set()
        await message.answer('Please enter the panel host:', reply_markup=back_keyboard_markup)

    elif message.text == "🔑 Password":

        await Form.password.set()
        await message.answer('Please enter your panel password:', reply_markup=back_keyboard_markup)

    elif message.text == "👤 Username":

        await Form.username.set()
        await message.answer('Please enter your panel username:', reply_markup=back_keyboard_markup)

    elif message.text == "➕ Add URL":

        # if len(admin_dict[str(user_id)].url) != 0:
        #     await message.answer(f'your current url is :\n{admin_dict[str(user_id)].url}')

        await Form.url.set()
        await message.answer('Please enter new url for links:', reply_markup=back_keyboard_markup)

    elif message.text == "ℹ️ Info":

        urls = ""
        counter = 1
        for k, v in admin_dict[str(user_id)].url.items():
            urls += f"{counter}. " + f"{k} , {v}" + "\n"
            counter += 1

        await message.reply(f'Username : {admin_dict[str(user_id)].username}\nPassword : {admin_dict[str(user_id)].password}\nHost : {admin_dict[str(user_id)].host}\nUrls :\n{urls}')

    elif message.text == "🔓 Login":

        if admin_dict[str(user_id)].username == "" or admin_dict[str(user_id)].password == "" or admin_dict[str(user_id)].host == "":
            await message.answer('Please first fill the information and then try again:')
            return

        try:
            payload = {"username": admin_dict[str(
                user_id)].username, "password": admin_dict[str(user_id)].password}
            post_url = admin_dict[str(user_id)].host + "/login"
            response = requests.post(post_url, data=payload)

            if response.json()["success"]:
                admin_dict[str(
                    user_id)].cookie = response.headers["Set-Cookie"].split(";")[0]
                await message.answer('Successful connection ✅')
                logging.info(f"user : {user_id} logined")
            else:
                logging.info(f"user : {user_id} failed to login")
                raise Exception(response.text)

        except:
            await message.answer('Connection failed, please try again')
            return

        update_db()


@ dp.message_handler(state=Form.host)
async def host(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].host = message.text

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered host_name")

    update_db()
    await Form.setting.set()
    await message.reply("Thank you, panel host has been submitted.", reply_markup=setting_keyboard_markup)


@ dp.message_handler(state=Form.password)
async def password(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].password = message.text

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered password")

    update_db()
    await Form.setting.set()
    await message.reply("Thank you, panel password has been submited.", reply_markup=setting_keyboard_markup)


@ dp.message_handler(state=Form.username)
async def username(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].username = message.text

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered username")

    update_db()
    await Form.setting.set()
    await message.reply("Thank you, panel username has been submited.", reply_markup=setting_keyboard_markup)


@ dp.message_handler(state=Form.url)
async def url(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    for k in admin_dict[str(user_id)].url.keys():
        if k == message.text:
            await Form.setting.set()
            await message.answer("This url already exists, please try again", reply_markup=setting_keyboard_markup)
            return

    admin_dict[str(user_id)].url[message.text] = "default"

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered url : {message.text}")

    # update_db()
    # await Form.setting.set()
    await Form.url_value.set()
    await message.reply("Please enter the name for this url:")


@ dp.message_handler(state=Form.url_value)
async def url_value(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    the_url = list(admin_dict[str(user_id)].url.keys())[-1]
    admin_dict[str(user_id)].url[the_url] = message.text

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered this value : {message.text} for this url : {the_url}")

    update_db()
    await Form.setting.set()

    await message.reply("Thank you, link url added successfully.", reply_markup=setting_keyboard_markup)


@ dp.message_handler(state=Form.generate)
async def generate(message: types.Message, state: FSMContext):

    if message.text == "Defualt":
        await Form.default.set()

    elif message.text == "Configurable":
        await Form.configurable.set()

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  choosed {message.text}")

    await message.answer("Please enter the name that you want to create link for:", reply_markup=back_keyboard_markup)


@ dp.message_handler(state=Form.default)
async def default(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].remark = message.text

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  choosed {message.text} as the remark")

    try:
        admin_dict[str(user_id)].id_user, admin_dict[str(user_id)].port = request_link(
            admin_dict[str(user_id)].host, admin_dict[str(user_id)].remark, admin_dict[str(user_id)].cookie)
    except:
        await message.answer('Conection failed, please try again')
        await Form.generate.set()
        await message.answer("Choose your config:", reply_markup=generate_keyboard_markup)
        return

    await Form.choose_url.set()

    choose_url_keyboard_markup = types.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True)
    choose_url_keyboard_markup.add(
        *(types.KeyboardButton(text) for text in admin_dict[str(user_id)].url.keys()))
    choose_url_keyboard_markup.add("🏠 Home")

    await message.answer("Choose your url:", reply_markup=choose_url_keyboard_markup)


@ dp.message_handler(state=Form.configurable)
async def configurable(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].remark = message.text

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  choosed {message.text} as the remark")

    await Form.max_traffic.set()
    await message.answer('Please enter user max traffic (GB):', reply_markup=back_keyboard_markup)


@ dp.message_handler(state=Form.max_traffic)
async def max_traffic(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].max_traffic = int(message.text)

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered {message.text} as max_traffic")

    await Form.device_limit.set()
    await message.answer('Please enter user device limit:', reply_markup=back_keyboard_markup)


@ dp.message_handler(state=Form.device_limit)
async def device_limit(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].device_limit = int(message.text)

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered {message.text} as device_limit")

    await Form.expire_time.set()
    await message.answer('Please enter expire time (Days):', reply_markup=back_keyboard_markup)


@ dp.message_handler(state=Form.expire_time)
async def expire_time(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    admin_dict[str(user_id)].expire_time = int(message.text)

    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  entered {message.text} as expire_time")

    try:
        admin_dict[str(user_id)].id_user, admin_dict[str(user_id)].port = request_link(
            admin_dict[str(user_id)].host, admin_dict[str(user_id)].remark, admin_dict[str(user_id)].cookie, admin_dict[str(user_id)].max_traffic, admin_dict[str(user_id)].device_limit, admin_dict[str(user_id)].expire_time)
    except:
        await message.answer('Conection failed, please try again')
        await Form.generate.set()
        await message.answer("Choose your config:", reply_markup=generate_keyboard_markup)
        return

    await Form.choose_url.set()

    choose_url_keyboard_markup = types.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True)
    choose_url_keyboard_markup.add(
        *(types.KeyboardButton(text) for text in admin_dict[str(user_id)].url.keys()))
    choose_url_keyboard_markup.add("🏠 Home")

    await message.answer("Choose link url from options below:", reply_markup=choose_url_keyboard_markup)


@ dp.message_handler(state=Form.choose_url)
async def choose_url(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    choosed_url = message.text
    remark = admin_dict[str(user_id)].remark + "-" + \
        admin_dict[str(user_id)].url[choosed_url]

    link = create_link(admin_dict[str(user_id)].id_user, choosed_url, admin_dict[str(
        user_id)].port, remark)

    await message.answer(f"`{link}`", parse_mode=ParseMode.MARKDOWN_V2)
    # await message.answer(link)
    logging.info(
        f"userid : {message.from_user.id}, username : {message.from_user.username}  created link : {link}")

    choose_url_keyboard_markup = types.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True)
    choose_url_keyboard_markup.add(
        *(types.KeyboardButton(text) for text in admin_dict[str(user_id)].url.keys()))
    choose_url_keyboard_markup.add("🏠 Home")

    await message.answer("Choose your url:", reply_markup=choose_url_keyboard_markup)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
