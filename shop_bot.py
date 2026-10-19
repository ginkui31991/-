import asyncio
import json
import os
import re
import time
from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands

try:
    from PIL import Image  # pip install pillow (그라데이션 이미지 생성용)
except ImportError:
    Image = None

# ───────────────────────── 설정 ─────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "MTQ5NzQ4NzQyMzE1MDYyMDc2Mg.Glrsm_.NPypVlARZ2rjm-g9hhgtHsrtOcEwouuxpgjH-M")
SHOP_NAME = "SPACE SHOP"
LOGO_URL = None                  # 패널 오른쪽 위 썸네일 이미지 주소 (없으면 None)

CHARGE_CHANNEL_ID = 1561693389924335716      # 충전 신청이 올라올 채널 ID
HISTORY_CHANNEL_ID = 1497449057323319402     # 감사 메시지가 올라올 채널 ID
ADMIN_ROLE_IDS = []              # 승인/재고충전/구매기록 가능한 역할 ID

# [수정 완료] 10,000원 = 1 X (1,000원당 0.1 X / 2,500원당 0.25 X)
WON_PER_X = 10000                 
DATA_FILE = "shop_data.json"

ACCOUNTS = {
    "제미": {"emoji": "💛", "bank": "카카오뱅크", "number": "7777029229132", "holder": "김서우"},
    "엑스": {"emoji": "🖤", "bank": "토스뱅크", "number": "1908-1421-6681", "holder": "이율"},
}

ROLE_DISCOUNTS = {}

PANEL_DESC = (
    "안내를 확인하신 뒤, 아래 버튼을 눌러 이용해 주세요.\n\n"
    "📌 **안내 채널**\n"
    "• 충전 방법: <#1561693747941613738>\n"
    "• 이용 규칙: <#1561693984613470248>\n\n"
    "⚠️ **이용 수칙**\n"
    "• 이용 전 **다이렉트 메시지(DM)** 허용 필수\n"
    "• 제품 개봉/이용 시 **영상 촬영**을 해주셔야 불량 보상이 가능합니다."
)
USAGE_DESC = (
    "• **충전** → 계좌 선택 → 입금 후 신청 → 승인 시 X 지급\n"
    "• **제품** → 카테고리 → 제품 선택 → 구매하기\n"
    "• **정보** → 내 잔액 및 구매 기록 확인\n"
    "• 기타 문의는 문의 티켓을 이용해 주세요."
)

CATEGORIES = {
    "discord": {
        "label": "디스코드", "emoji": "💎",
        "products": [
            {"name": "디스코드 데코", "price": 0.2, "type": "unlimited", "desc": "프로필 데코레이션", "aliases": []},
            {"name": "니트로 프라임", "price": 0.6, "type": "count", "desc": "디스코드 니트로 프라임", "aliases": []},
            {"name": "니트로 베이직", "price": 0.3, "type": "count", "desc": "디스코드 니트로 베이직", "aliases": []},
            {"name": "서버부스트", "price": 0.3, "type": "count", "desc": "디스코드 서버 부스트", "aliases": ["서버 부스트"]},
            {"name": "디스코드 멤버", "price": 0.2, "type": "unlimited", "desc": "서버 멤버 서비스", "aliases": []},
            {"name": "디스코드 툴", "price": 0.4, "type": "count", "desc": "디스코드 관련 툴", "aliases": ["디스코드 tools", "discord tools"]},
        ],
    },
    "ott": {
        "label": "스트리밍 / 구독", "emoji": "🎬",
        "products": [
            {"name": "스포티파이", "price": 0.5, "type": "account", "id_format": "email", "pw_min": 8, "desc": "스포티파이 프리미엄 구독", "aliases": []},
            {"name": "유튜브 프리미엄", "price": 0.5, "type": "account", "id_format": "email", "pw_min": 8, "desc": "광고 없는 유튜브 프리미엄", "aliases": []},
            {"name": "넷플릭스", "price": 0.8, "type": "account", "id_format": "email", "pw_min": 6, "desc": "넷플릭스 프리미엄", "aliases": []},
            {"name": "디즈니 패키지", "price": 0.3, "type": "account", "id_format": "email", "pw_min": 6, "desc": "Disney+, Hulu, ESPN+ 패키지 계정 (영구 이용, VPN 필요 가능)", "aliases": ["디즈니 묶음", "디즈니패키지"]},
            {"name": "디즈니 단독", "price": 0.25, "type": "account", "id_format": "email", "pw_min": 6, "desc": "Disney+ 단독 계정 (평생 이용, VPN 필요 가능)", "aliases": ["디즈니플러스", "디즈니 단독 계정"]},
            {"name": "CapCut Pro", "price": 0.5, "type": "account", "id_format": "email", "pw_min": 8, "desc": "캡컷 프로 구독", "aliases": ["캡컷"]},
        ],
    },
    "ai": {
        "label": "AI", "emoji": "🤖",
        "products": [
            {"name": "ChatGPT Plus", "price": 1.5, "type": "count", "desc": "ChatGPT 플러스 계정", "aliases": []},
            {"name": "Gemini Pro", "price": 1.2, "type": "count", "desc": "제미나이 프로 계정", "aliases": []},
            {"name": "Claude Pro", "price": 1.5, "type": "count", "desc": "Claude 프로 계정", "aliases": ["클로드"]},
        ],
    },
    "game": {
        "label": "게임", "emoji": "🎮",
        "products": [
            {"name": "마인크래프트 계정", "price": 0.9, "type": "count", "desc": "마인크래프트 정품 계정", "aliases": []},
            {"name": "GTA", "price": 1.0, "type": "count", "desc": "GTA 게임 계정", "aliases": []},
            {"name": "로블록스 에셋", "price": 0.3, "type": "count", "desc": "로블록스 디자인/스크립트 에셋", "aliases": []},
        ],
    },
    "etc": {
        "label": "기타", "emoji": "🌐",
        "products": [
            {"name": "호스팅", "price": 0.4, "type": "unlimited", "desc": "24시간 서버 호스팅", "aliases": []},
            {"name": "VPN", "price": 0.5, "type": "unlimited", "desc": "고속 VPN 서비스", "aliases": []},
            {"name": "봇 주문제작", "price": 3.0, "type": "unlimited", "desc": "맞춤형 디스코드 봇 제작", "aliases": ["봇-주문제작", "봇주문"]},
            {"name": "자료", "price": 0.2, "type": "count", "desc": "각종 개발/설정 자료", "aliases": []},
        ],
    },
}

PURPLE = 0xA855F7
PINK = 0xF472B6
GREEN = 0x2ECC71
RED = 0xE74C3C
GRADIENT_STOPS = [(139, 92, 246), (192, 132, 252), (244, 114, 182)]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PRICE_RE = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*\)")
PURCHASE_LOCK = asyncio.Lock()


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


ALL_PRODUCTS = {p["name"]: p for c in CATEGORIES.values() for p in c["products"]}
PRODUCT_CATEGORY = {p["name"]: k for k, c in CATEGORIES.items() for p in c["products"]}
NAME_INDEX = sorted(
    [(norm(n), p) for p in ALL_PRODUCTS.values() for n in [p["name"], *p.get("aliases", [])]],
    key=lambda x: -len(x[0]),
)


# ───────────────────────── 그라데이션 이미지 ─────────────────────────
def build_gradient(width: int = 900, height: int = 14):
    if Image is None:
        return None
    img = Image.new("RGB", (width, height))
    seg = len(GRADIENT_STOPS) - 1
    for x in range(width):
        t = x / (width - 1) * seg
        i = min(int(t), seg - 1)
        f = t - i
        c1, c2 = GRADIENT_STOPS[i], GRADIENT_STOPS[i + 1]
        color = tuple(int(c1[k] + (c2[k] - c1[k]) * f) for k in range(3))
        img.paste(color, (x, 0, x + 1, height))
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


GRADIENT_PNG = build_gradient()


def deco(embed: discord.Embed) -> discord.Embed:
    if GRADIENT_PNG:
        embed.set_image(url="attachment://grad.png")
    return embed


def grad_kwargs() -> dict:
    if GRADIENT_PNG:
        return {"file": discord.File(BytesIO(GRADIENT_PNG), filename="grad.png")}
    return {}


# ───────────────────────── 데이터 저장 ─────────────────────────
def load_data() -> dict:
    data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    for k in ("balances", "pending", "stock", "history", "charged", "prices"):
        data.setdefault(k, {})
    return data


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ───────────────────────── 유틸 ─────────────────────────
def is_admin(member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    return any(r.id in ADMIN_ROLE_IDS for r in member.roles)


def get_discount(member) -> int:
    if not isinstance(member, discord.Member):
        return 0
    return max((ROLE_DISCOUNTS.get(r.id, 0) for r in member.roles), default=0)


def get_product_price(product: dict) -> float:
    data = load_data()
    return data["prices"].get(product["name"], product["price"])


def discounted_price(product: dict, member) -> float:
    base_price = get_product_price(product)
    return round(base_price * (100 - get_discount(member)) / 100, 2)


def fmt_x(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{s} X"


def stock_count(product: dict, data: dict):
    if product["type"] == "unlimited":
        return None
    v = data["stock"].get(product["name"])
    if product["type"] == "account":
        return len(v or [])
    return v or 0


def stock_text(count) -> str:
    if count is None:
        return "무제한"
    if count <= 0:
        return "품절"
    return f"{count}개"


def find_product(text: str):
    t = norm(text)
    for n, p in NAME_INDEX:
        if n in t:
            return p
    return None


def order_channel(client):
    return client.get_channel(HISTORY_CHANNEL_ID)


def validate_account(product: dict, acc_id: str, pw: str, data: dict):
    if not acc_id or re.search(r"\s", acc_id):
        return "아이디에 공백이 있거나 비어 있어요."
    if product.get("id_format") == "email" and not EMAIL_RE.match(acc_id):
        return "아이디는 이메일 형식이어야 해요. (예: example@gmail.com)"
    need = product.get("pw_min", 6)
    if len(pw) < need:
        return f"비밀번호는 {need}자 이상이어야 해요."
    if re.search(r"\s", pw):
        return "비밀번호에 공백이 있어요."
    existing = data["stock"].get(product["name"], [])
    if any(a["id"].lower() == acc_id.lower() for a in existing):
        return "이미 등록된 계정이에요."
    return None


# ───────────────────────── 임베드 디자인 ─────────────────────────
def panel_embed() -> discord.Embed:
    e = discord.Embed(title=f"✨ {SHOP_NAME}", description=PANEL_DESC, color=PURPLE)
    if LOGO_URL:
        e.set_thumbnail(url=LOGO_URL)
    return deco(e)


def category_embed() -> discord.Embed:
    return deco(discord.Embed(title="🛍️ 카테고리 선택", description="원하시는 상품의 카테고리를 아래 메뉴에서 선택해 주세요.", color=PURPLE))


def product_list_embed(key: str, member) -> discord.Embed:
    data = load_data()
    lines = []
    for p in CATEGORIES[key]["products"]:
        price = discounted_price(p, member)
        lines.append(f"• **{p['name']}** │ `{fmt_x(price)}` │ 재고 `{stock_text(stock_count(p, data))}`")
    cat = CATEGORIES[key]
    e = discord.Embed(
        title=f"{cat['emoji']} {cat['label']} 상품 목록",
        description="\n".join(lines) + "\n\n──────────────────────────────\n아래 선택 메뉴에서 **구매할 제품**을 선택해 주세요 💖",
        color=PINK,
    )
    e.set_footer(text=f"현재 적용 할인율: {get_discount(member)}%")
    return deco(e)


def product_desc_embed(key: str) -> discord.Embed:
    cat = CATEGORIES[key]
    lines = [f"📌 **{p['name']}**\n└ {p['desc']}" for p in cat["products"]]
    return deco(discord.Embed(title=f"{cat['emoji']} {cat['label']} 상세 설명", description="\n\n".join(lines), color=PURPLE))


def confirm_embed(product: dict, member) -> discord.Embed:
    data = load_data()
    price = discounted_price(product, member)
    balance = data["balances"].get(str(member.id), 0)
    after_balance = round(balance - price, 2)

    e = discord.Embed(
        title=f"🛒 {product['name']}",
        description=f"```text\n{product['desc']}\n```",
        color=PINK
    )
    e.add_field(name="💖 판매 가격", value=f"`{fmt_x(price)}`", inline=True)
    e.add_field(name="💰 보유 잔액", value=f"`{fmt_x(balance)}`", inline=True)
    
    if balance + 1e-9 >= price:
        e.add_field(name="🧾 결제 후 잔액", value=f"`{fmt_x(after_balance)}`", inline=True)
    else:
        e.add_field(name="⚠️ 부족한 금액", value=f"`{fmt_x(round(price - balance, 2))}`", inline=True)
        e.set_footer(text="❌ 잔액이 부족합니다. 메인 패널의 [충전] 버튼을 이용해 주세요.")

    e.add_field(name="📦 남은 재고", value=f"`{stock_text(stock_count(product, data))}`", inline=False)
    return deco(e)


def purchase_fail_embed(reason: str) -> discord.Embed:
    return deco(discord.Embed(title="❌ 구매 실패", description=reason, color=RED))


def account_embed(key: str) -> discord.Embed:
    a = ACCOUNTS[key]
    e = discord.Embed(
        title=f"{a['emoji']} {key} 결제 안내",
        description="아래 계좌로 입금하신 후 **충전 신청** 버튼을 눌러주세요.",
        color=PURPLE,
    )
    e.add_field(name="은행", value=a["bank"], inline=True)
    e.add_field(name="예금주", value=a["holder"], inline=True)
    e.add_field(name="계좌번호", value=f"```{a['number']}```", inline=False)
    e.set_footer(text="환율 기준: 1,000원 = 0.1 X (10,000원 = 1 X)")
    return deco(e)


def info_embed(user: discord.abc.User, member) -> discord.Embed:
    data = load_data()
    uid = str(user.id)
    balance = data["balances"].get(uid, 0)
    charged = data["charged"].get(uid, 0)
    history = data["history"].get(uid, [])[-10:][::-1]

    e = discord.Embed(title="💜 내 계정 정보", color=PURPLE)
    e.set_thumbnail(url=user.display_avatar.url)
    e.add_field(name="💰 보유 잔액", value=f"**{fmt_x(balance)}**", inline=True)
    e.add_field(name="📥 누적 충전액", value=fmt_x(charged), inline=True)
    e.add_field(name="🏷️ 적용 할인율", value=f"{get_discount(member)}%", inline=True)
    
    if history:
        lines = [f"• **{h['product']}** │ `{fmt_x(h['amount'])}` │ <t:{h['ts']}:d>" for h in history]
        e.add_field(name="🧾 최근 구매 내역 (최대 10건)", value="\n".join(lines), inline=False)
    else:
        e.add_field(name="🧾 최근 구매 내역", value="구매 내역이 존재하지 않습니다.", inline=False)
    return deco(e)


def channel_thank_you_embed(user: discord.abc.User, product: dict, price: float) -> discord.Embed:
    e = discord.Embed(
        title="🎉 구매해 주셔서 진심으로 감사드립니다!",
        description=(
            f"**{user.mention}**님께서 **{product['name']}** 상품을 구매하셨습니다! 💖\n"
            f"저희 상점을 이용해 주셔서 감사드리며, 소중히 사용하시길 바랍니다 ✨"
        ),
        color=PINK
    )
    e.add_field(name="📦 구매 상품", value=f"`{product['name']}`", inline=True)
    e.add_field(name="💵 결제 금액", value=f"`{fmt_x(price)}`", inline=True)
    e.set_footer(text="💌 상세 정보 및 계정 내역은 DM으로 안전하게 발송되었습니다.")
    return deco(e)


def dm_receipt_embed(product: dict, price: float, new_balance: float, account: dict = None) -> discord.Embed:
    e = discord.Embed(
        title="🧾 구매 내역 및 전달 사항",
        description=f"안녕하세요! 요청하신 **{product['name']}** 상품 결제가 성공적으로 완료되었습니다.",
        color=PURPLE,
    )
    e.add_field(name="🛍️ 상품명", value=f"**{product['name']}**", inline=True)
    e.add_field(name="💳 차감 금액", value=f"`{fmt_x(price)}`", inline=True)
    e.add_field(name="💰 남은 잔액", value=f"`{fmt_x(new_balance)}`", inline=True)

    if account is not None:
        e.add_field(
            name="🔑 전달된 계정 정보",
            value=f"```text\n아이디  : {account['id']}\n비밀번호: {account['pw']}\n```",
            inline=False
        )
        e.add_field(name="⚠️ 이용 주의사항", value="• 상품 사용 전 **동영상 녹화**를 해주셔야 불량 발생 시 A/S 및 보상이 가능합니다.", inline=False)
    else:
        e.add_field(name="ℹ️ 안내", value="• 관리자 수동 지급 상품입니다. 확인 후 순차적으로 지급해 드립니다.", inline=False)

    e.set_footer(text="문의 사항이 있으신 경우 서버 내 문의 티켓을 이용해 주세요 ✨")
    return e


def stock_status_embed() -> discord.Embed:
    data = load_data()
    lines = []
    for cat in CATEGORIES.values():
        for p in cat["products"]:
            price = get_product_price(p)
            if p["type"] == "unlimited":
                lines.append(f"{cat['emoji']} **{p['name']}** │ `{fmt_x(price)}` │ 무제한")
            else:
                kind = "계정" if p["type"] == "account" else "수량"
                lines.append(f"{cat['emoji']} **{p['name']}** │ `{fmt_x(price)}` │ `{stock_count(p, data)}개` ({kind})")
    return discord.Embed(
        title="📦 재고 및 가격 현황 목록",
        description="\n".join(lines) or "등록된 상품이 없습니다.",
        color=PURPLE,
    )


# ───────────────────────── 구매 처리 로직 ─────────────────────────
async def perform_purchase(interaction: discord.Interaction, product: dict):
    user = interaction.user
    uid = str(user.id)
    name = product["name"]
    price = discounted_price(product, user)

    async with PURCHASE_LOCK:
        data = load_data()
        balance = data["balances"].get(uid, 0)
        
        if balance + 1e-9 < price:
            return purchase_fail_embed(
                f"X가 부족합니다. (보유: `{fmt_x(balance)}` / 필요: `{fmt_x(price)}`)\n메인 패널의 **[충전]** 버튼을 통해 충전해 주세요."
            ), False

        count = stock_count(product, data)
        if count is not None and count <= 0:
            return purchase_fail_embed(f"현재 **{name}** 상품은 품절 상태입니다."), False

        account = None
        if product["type"] == "account":
            account = data["stock"][name].pop(0)
        elif product["type"] == "count":
            data["stock"][name] = count - 1

        data["balances"][uid] = round(balance - price, 2)
        rec = {"product": name, "amount": price, "ts": int(time.time()), "via": "bot"}
        data["history"].setdefault(uid, []).append(rec)
        save_data(data)
        new_balance = data["balances"][uid]

        # 1. 구매 내역 DM 발송
        try:
            await user.send(embed=dm_receipt_embed(product, price, new_balance, account))
        except discord.HTTPException:
            # DM 수신 불가 시 구매 복구
            data = load_data()
            data["balances"][uid] = round(data["balances"].get(uid, 0) + price, 2)
            if account is not None:
                data["stock"].setdefault(name, []).insert(0, account)
            elif product["type"] == "count":
                data["stock"][name] = data["stock"].get(name, 0) + 1
            hist = data["history"].get(uid, [])
            if rec in hist:
                hist.remove(rec)
            save_data(data)
            return purchase_fail_embed(
                "구매자님의 **DM이 차단**되어 있어 상품을 발송할 수 없습니다.\n[서버 멤버가 보내는 DM 허용] 설정 후 다시 시도해 주세요.\n(차감된 X는 복구되었습니다)"
            ), False

    # 2. 지정된 채널 (1497449057323319402)에 감사 알림 출력
    ch = order_channel(interaction.client)
    if ch:
        try:
            await ch.send(embed=channel_thank_you_embed(user, product, price))
        except discord.HTTPException:
            pass

    e = discord.Embed(title="✅ 결제 성공", color=GREEN)
    e.add_field(name="상품명", value=f"**{name}**", inline=True)
    e.add_field(name="결제 금액", value=f"`{fmt_x(price)}`", inline=True)
    e.add_field(name="남은 잔액", value=f"`{fmt_x(new_balance)}`", inline=True)
    e.description = "구매해 주셔서 감사합니다! 상세 정보는 **개인 DM**을 확인해 주세요 💜"
    return deco(e), True


# ───────────────────────── 제품 UI 흐름 ─────────────────────────
class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=c["label"], value=k, emoji=c["emoji"])
            for k, c in CATEGORIES.items()
        ]
        super().__init__(placeholder="카테고리를 선택하세요.", options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        await interaction.response.edit_message(
            embed=product_list_embed(key, interaction.user), view=ProductListView(key, interaction.user)
        )


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CategorySelect())


class ProductSelect(discord.ui.Select):
    def __init__(self, key: str, member):
        data = load_data()
        emoji = CATEGORIES[key]["emoji"]
        options = []
        for p in CATEGORIES[key]["products"]:
            desc = f"{fmt_x(discounted_price(p, member))} │ 재고: {stock_text(stock_count(p, data))}"
            options.append(discord.SelectOption(label=p["name"], value=p["name"], emoji=emoji, description=desc[:100]))
        super().__init__(placeholder="구매할 상품을 선택하세요.", options=options)

    async def callback(self, interaction: discord.Interaction):
        product = ALL_PRODUCTS[self.values[0]]
        await interaction.response.edit_message(
            embed=confirm_embed(product, interaction.user), view=ConfirmView(product)
        )


class ProductListView(discord.ui.View):
    def __init__(self, key: str, member):
        super().__init__(timeout=300)
        self.key = key
        self.add_item(ProductSelect(key, member))

    @discord.ui.button(label="상품 설명 보기", emoji="💜", style=discord.ButtonStyle.secondary)
    async def desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=product_desc_embed(self.key), view=BackView())


class ConfirmView(discord.ui.View):
    def __init__(self, product: dict):
        super().__init__(timeout=300)
        self.product = product

    @discord.ui.button(label="구매확정", emoji="💗", style=discord.ButtonStyle.primary)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        embed, ok = await perform_purchase(interaction, self.product)
        if ok:
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
        else:
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=BackView())

    @discord.ui.button(label="돌아가기", emoji="◀️", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        key = PRODUCT_CATEGORY[self.product["name"]]
        await interaction.response.edit_message(
            embed=product_list_embed(key, interaction.user), view=ProductListView(key, interaction.user)
        )


class BackView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="카테고리로", emoji="◀️", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=category_embed(), view=CategoryView())


# ───────────────────────── 충전 흐름 ─────────────────────────
class TransferModal(discord.ui.Modal, title="계좌이체 충전 신청"):
    name = discord.ui.TextInput(label="입금자명", required=True, max_length=20)
    amount = discord.ui.TextInput(label="입금 금액 (원)", required=True, max_length=10)
    purpose = discord.ui.TextInput(
        label="충전 목적", placeholder="예: 니트로 구매", required=True, max_length=100
    )

    def __init__(self, account_key: str):
        super().__init__()
        self.account_key = account_key

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.amount.value.replace(",", "").replace("원", "").strip()
        if not raw.isdigit() or int(raw) <= 0:
            return await interaction.response.send_message("금액은 숫자만 입력해 주세요.", ephemeral=True)
        won = int(raw)
        x = round(won / WON_PER_X, 2)

        ch = interaction.client.get_channel(CHARGE_CHANNEL_ID)
        if ch is None:
            return await interaction.response.send_message("충전 관리 채널이 설정되지 않았습니다.", ephemeral=True)

        e = discord.Embed(title="💳 충전 신청 접수", color=PURPLE)
        e.add_field(name="신청자", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        e.add_field(name="입금자명", value=self.name.value, inline=True)
        e.add_field(name="입금 금액", value=f"{won:,}원", inline=True)
        e.add_field(name="지급될 X", value=fmt_x(x), inline=True)
        e.add_field(name="선택 계좌", value=self.account_key, inline=True)
        e.add_field(name="충전 목적", value=self.purpose.value, inline=False)
        msg = await ch.send(embed=e, view=ApprovalView())

        data = load_data()
        data["pending"][str(msg.id)] = {
            "user_id": interaction.user.id,
            "won": won,
            "x": x,
            "name": self.name.value,
            "account": self.account_key,
            "purpose": self.purpose.value,
        }
        save_data(data)

        done = discord.Embed(
            title="✅ 충전 신청 완료",
            description=f"**{won:,}원** → **{fmt_x(x)}** 충전 신청이 접수되었습니다.\n입금 확인 후 승인되면 DM과 함께 잔액에 반영됩니다.",
            color=GREEN,
        )
        await interaction.response.send_message(embed=done, ephemeral=True)


class CouponModal(discord.ui.Modal, title="쿠폰 입력"):
    code = discord.ui.TextInput(label="쿠폰 코드", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.client.get_channel(CHARGE_CHANNEL_ID)
        if ch:
            e = discord.Embed(title="🎟️ 쿠폰 사용 요청", color=PURPLE)
            e.add_field(name="신청자", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            e.add_field(name="쿠폰 코드", value=f"`{self.code.value}`", inline=False)
            await ch.send(embed=e)
        await interaction.response.send_message("쿠폰 신청이 완료되었습니다.", ephemeral=True)


def account_choose_embed() -> discord.Embed:
    return deco(discord.Embed(title="💗 입금 계좌 선택", description="입금하실 계좌를 선택해 주세요.", color=PINK))


class AccountDetailView(discord.ui.View):
    def __init__(self, key: str):
        super().__init__(timeout=300)
        self.key = key

    @discord.ui.button(label="충전 신청하기", emoji="💳", style=discord.ButtonStyle.primary)
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TransferModal(self.key))

    @discord.ui.button(label="뒤로가기", emoji="◀️", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=account_choose_embed(), view=AccountChooseView())


class AccountChooseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def _show(self, interaction: discord.Interaction, key: str):
        await interaction.response.edit_message(embed=account_embed(key), view=AccountDetailView(key))

    @discord.ui.button(label="제미", emoji="💛", style=discord.ButtonStyle.primary)
    async def jemi(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "제미")

    @discord.ui.button(label="엑스", emoji="🖤", style=discord.ButtonStyle.secondary)
    async def ex(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "엑스")


class ChargeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="계좌이체", emoji="🏦", style=discord.ButtonStyle.primary)
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=account_choose_embed(), view=AccountChooseView())

    @discord.ui.button(label="쿠폰 사용", emoji="🎟️", style=discord.ButtonStyle.secondary)
    async def coupon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CouponModal())


# ───────────────────────── 관리자 충전 승인 ─────────────────────────
class ApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _notify(self, interaction: discord.Interaction, user_id: int, embed: discord.Embed):
        try:
            user = await interaction.client.fetch_user(user_id)
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="승인", emoji="✅", style=discord.ButtonStyle.success, custom_id="charge:approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

        data = load_data()
        req = data["pending"].pop(str(interaction.message.id), None)
        if req is None:
            return await interaction.response.send_message("이미 처리된 신청건입니다.", ephemeral=True)

        uid = str(req["user_id"])
        data["balances"][uid] = round(data["balances"].get(uid, 0) + req["x"], 2)
        data["charged"][uid] = round(data["charged"].get(uid, 0) + req["x"], 2)
        save_data(data)

        e = interaction.message.embeds[0]
        e.title = "✅ 충전 승인 완료"
        e.color = GREEN
        e.add_field(name="처리자", value=interaction.user.mention, inline=True)
        e.add_field(name="현재 잔액", value=fmt_x(data["balances"][uid]), inline=True)
        await interaction.response.edit_message(embed=e, view=None)

        dm = discord.Embed(
            title="🎉 충전 완료 안내",
            description=f"**{fmt_x(req['x'])}** 충전이 완료되었습니다.\n현재 보유 잔액: **{fmt_x(data['balances'][uid])}**",
            color=GREEN,
        )
        await self._notify(interaction, req["user_id"], dm)

    @discord.ui.button(label="거절", emoji="❌", style=discord.ButtonStyle.danger, custom_id="charge:reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

        data = load_data()
        req = data["pending"].pop(str(interaction.message.id), None)
        if req is None:
            return await interaction.response.send_message("이미 처리된 신청건입니다.", ephemeral=True)
        save_data(data)

        e = interaction.message.embeds[0]
        e.title = "❌ 충전 거절됨"
        e.color = RED
        e.add_field(name="처리자", value=interaction.user.mention, inline=True)
        await interaction.response.edit_message(embed=e, view=None)

        dm = discord.Embed(
            title="❌ 충전 거절 안내",
            description=f"**{req['won']:,}원** 충전 신청이 거절되었습니다.\n사유 문의는 티켓을 열어주세요.",
            color=RED,
        )
        await self._notify(interaction, req["user_id"], dm)


# ───────────────────────── 가격 및 재고 관리 ─────────────────────────
class PriceChangeModal(discord.ui.Modal):
    def __init__(self, product: dict):
        super().__init__(title=f"{product['name']} 가격 변경"[:45])
        self.product = product
        curr_price = get_product_price(product)
        self.new_price = discord.ui.TextInput(
            label="새로운 가격 (X)",
            placeholder=f"현재 가격: {curr_price} X",
            max_length=10
        )
        self.add_item(self.new_price)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        raw = self.new_price.value.strip()
        try:
            val = round(float(raw), 2)
            if val < 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ 가격은 0 이상의 숫자로 입력해 주세요.", ephemeral=True)

        data = load_data()
        data["prices"][self.product["name"]] = val
        save_data(data)

        e = discord.Embed(
            title="✅ 가격 변경 완료",
            description=f"**{self.product['name']}** 상품의 가격이 **{fmt_x(val)}** 로 변경되었습니다.",
            color=GREEN,
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


class PriceSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for cat in CATEGORIES.values():
            for p in cat["products"]:
                curr_price = get_product_price(p)
                options.append(
                    discord.SelectOption(
                        label=p["name"],
                        value=p["name"],
                        emoji=cat["emoji"],
                        description=f"현재 가격: {fmt_x(curr_price)}",
                    )
                )
        super().__init__(placeholder="가격을 변경할 상품을 선택하세요.", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        product = ALL_PRODUCTS[self.values[0]]
        await interaction.response.send_modal(PriceChangeModal(product))


class PriceSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(PriceSelect())


class AccountStockModal(discord.ui.Modal):
    def __init__(self, product: dict):
        super().__init__(title=f"{product['name']} 재고 충전"[:45])
        self.product = product
        self.acc_id = discord.ui.TextInput(label="계정 아이디", placeholder="example@gmail.com", max_length=100)
        self.acc_pw = discord.ui.TextInput(label="비밀번호", max_length=64)
        self.add_item(self.acc_id)
        self.add_item(self.acc_pw)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        acc_id = self.acc_id.value.strip()
        pw = self.acc_pw.value.strip()

        data = load_data()
        err = validate_account(self.product, acc_id, pw, data)
        if err:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)

        data["stock"].setdefault(self.product["name"], []).append({"id": acc_id, "pw": pw})
        save_data(data)
        count = len(data["stock"][self.product["name"]])
        e = discord.Embed(
            title="✅ 재고 추가 완료",
            description=f"**{self.product['name']}** 계정이 추가되었습니다.\n현재 재고: **{count}개**",
            color=GREEN,
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


class CountStockModal(discord.ui.Modal):
    def __init__(self, product: dict):
        super().__init__(title=f"{product['name']} 재고 충전"[:45])
        self.product = product
        self.qty = discord.ui.TextInput(label="추가할 수량", placeholder="예: 5", max_length=4)
        self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        raw = self.qty.value.strip()
        if not raw.isdigit() or int(raw) <= 0:
            return await interaction.response.send_message("❌ 수량은 1 이상의 숫자로 입력해 주세요.", ephemeral=True)

        data = load_data()
        name = self.product["name"]
        data["stock"][name] = data["stock"].get(name, 0) + int(raw)
        save_data(data)
        e = discord.Embed(
            title="✅ 재고 추가 완료",
            description=f"**{name}** 재고 {int(raw)}개가 추가되었습니다.\n현재 재고: **{data['stock'][name]}개**",
            color=GREEN,
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


class StockSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for cat in CATEGORIES.values():
            for p in cat["products"]:
                if p["type"] == "unlimited":
                    continue
                options.append(
                    discord.SelectOption(
                        label=p["name"],
                        value=p["name"],
                        emoji=cat["emoji"],
                        description="계정 입력" if p["type"] == "account" else "수량 입력",
                    )
                )
        super().__init__(placeholder="재고를 충전할 상품을 선택하세요.", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        product = ALL_PRODUCTS[self.values[0]]
        modal = AccountStockModal(product) if product["type"] == "account" else CountStockModal(product)
        await interaction.response.send_modal(modal)


class StockSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(StockSelect())


class StockPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="재고 충전", emoji="📦", style=discord.ButtonStyle.primary, custom_id="stock:open")
    async def open_stock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        e = discord.Embed(title="📦 재고 충전", description="재고를 추가할 상품을 아래에서 선택해 주세요.", color=PURPLE)
        await interaction.response.send_message(embed=e, view=StockSelectView(), ephemeral=True)

    @discord.ui.button(label="가격 변경", emoji="💲", style=discord.ButtonStyle.success, custom_id="stock:price")
    async def open_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        e = discord.Embed(title="💲 상품 가격 변경", description="가격을 변경할 상품을 아래에서 선택해 주세요.", color=PURPLE)
        await interaction.response.send_message(embed=e, view=PriceSelectView(), ephemeral=True)

    @discord.ui.button(label="현황 확인", emoji="📋", style=discord.ButtonStyle.secondary, custom_id="stock:status")
    async def stock_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
        await interaction.response.send_message(embed=stock_status_embed(), ephemeral=True)


# ───────────────────────── 메인 패널 UI ─────────────────────────
class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="제품", emoji="💜", style=discord.ButtonStyle.primary, custom_id="shop:products")
    async def products(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=category_embed(), view=CategoryView(), ephemeral=True, **grad_kwargs()
        )

    @discord.ui.button(label="충전", emoji="💗", style=discord.ButtonStyle.primary, custom_id="shop:charge")
    async def charge(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = deco(discord.Embed(title="💗 충전 수단 선택", description="원하시는 충전 방식을 선택해 주세요.", color=PINK))
        await interaction.response.send_message(embed=e, view=ChargeView(), ephemeral=True, **grad_kwargs())

    @discord.ui.button(label="정보", emoji="💖", style=discord.ButtonStyle.primary, custom_id="shop:info")
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=info_embed(interaction.user, interaction.user), ephemeral=True, **grad_kwargs()
        )

    @discord.ui.button(label="이용", emoji="💞", style=discord.ButtonStyle.primary, custom_id="shop:usage")
    async def usage(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = deco(discord.Embed(title="💞 이용 가이드", description=USAGE_DESC, color=PURPLE))
        await interaction.response.send_message(embed=e, ephemeral=True, **grad_kwargs())


# ───────────────────────── 구매 기록 감지 ─────────────────────────
def parse_purchase(message: discord.Message):
    buyer = next((m for m in message.mentions if not m.bot), None)
    amounts = PRICE_RE.findall(message.content)
    if buyer is None or not amounts:
        return "ignore", None, None, None
    amount = round(float(amounts[-1]), 2)
    product = find_product(re.sub(r"<@!?\d+>", "", message.content))
    if product is None:
        return "no_product", buyer, None, amount
    if amount <= 0:
        return "bad_amount", buyer, product, amount
    return "ok", buyer, product, amount


def is_duplicate(hist: list, msg_id: int, name: str, amount: float, ts: int) -> bool:
    for h in hist:
        if h.get("msg_id") == msg_id:
            return True
        if "msg_id" not in h and h["product"] == name and abs(h["amount"] - amount) < 1e-9 and abs(h["ts"] - ts) <= 120:
            return True
    return False


async def fail(message: discord.Message, reason: str):
    try:
        await message.add_reaction("❌")
    except discord.HTTPException:
        pass
    await message.reply(reason, mention_author=False)


async def handle_purchase(message: discord.Message):
    status, buyer, product, amount = parse_purchase(message)
    if status == "ignore":
        return
    if status == "no_product":
        return await fail(message, "제품명을 인식하지 못했습니다. 등록된 정식 제품명으로 입력해 주세요.")
    if status == "bad_amount":
        return await fail(message, "금액은 0보다 커야 합니다.")

    uid = str(buyer.id)
    notes = []

    account = None
    data = load_data()
    if product["type"] == "account":
        stocked = data["stock"].get(product["name"], [])
        if stocked:
            account = stocked[0]
            notes.append("계정 정보를 DM으로 발송했습니다.")
        else:
            notes.append("ℹ️ 등록된 계정 재고가 없습니다.")

    data = load_data()
    balance = data["balances"].get(uid, 0)
    deduct = min(balance, amount)
    if deduct + 1e-9 < amount:
        notes.append(f"⚠️ 잔액 부족으로 {fmt_x(deduct)}만 차감되었습니다.")
    data["balances"][uid] = round(balance - deduct, 2)

    name = product["name"]
    if product["type"] == "account":
        if account is not None:
            data["stock"][name] = [a for a in data["stock"].get(name, []) if a["id"] != account["id"]]
    elif product["type"] == "count":
        left = data["stock"].get(name, 0)
        if left > 0:
            data["stock"][name] = left - 1
        else:
            notes.append("ℹ️ 재고 수량이 부족합니다.")

    data["history"].setdefault(uid, []).append(
        {
            "product": name,
            "amount": amount,
            "ts": int(message.created_at.timestamp()),
            "admin_id": message.author.id,
            "msg_id": message.id,
        }
    )
    save_data(data)
    new_balance = data["balances"][uid]

    try:
        await buyer.send(embed=dm_receipt_embed(product, amount, new_balance, account))
        notes.append("구매 내역 DM 전송 완료")
    except discord.HTTPException:
        notes.append("⚠️ 구매자 DM 차단으로 인해 메시지를 보내지 못했습니다.")

    try:
        await message.add_reaction("✅")
    except discord.HTTPException:
        pass

    e = discord.Embed(title="✅ 구매 수동 기록 완료", color=GREEN)
    e.add_field(name="구매자", value=buyer.mention, inline=True)
    e.add_field(name="제품명", value=name, inline=True)
    e.add_field(name="차감 금액", value=fmt_x(amount), inline=True)
    e.add_field(name="남은 잔액", value=fmt_x(new_balance), inline=True)
    if abs(amount - get_product_price(product)) > 1e-9:
        notes.insert(0, f"⚠️ 정가({fmt_x(get_product_price(product))})와 처리된 금액이 다릅니다.")
    if notes:
        e.set_footer(text="\n".join(notes))
    await message.reply(embed=e, mention_author=False)


# ───────────────────────── 봇 메인 실행 ─────────────────────────
class ShopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(MainView())
        self.add_view(ApprovalView())
        self.add_view(StockPanelView())
        await self.tree.sync()


bot = ShopBot()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return
    if message.channel.id != HISTORY_CHANNEL_ID:
        return
    if not is_admin(message.author):
        return
    async with PURCHASE_LOCK:
        await handle_purchase(message)


@bot.tree.command(name="패널", description="제품 판매 패널을 이 채널에 올립니다")
@app_commands.default_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    await interaction.channel.send(embed=panel_embed(), view=MainView(), **grad_kwargs())
    await interaction.response.send_message("패널을 전송했습니다!", ephemeral=True)


@bot.tree.command(name="재고패널", description="관리자 전용 재고 및 가격 관리 패널을 이 채널에 올립니다")
@app_commands.default_permissions(administrator=True)
async def stock_panel(interaction: discord.Interaction):
    e = stock_status_embed()
    e.title = "📦 재고 및 가격 관리 (관리자 전용)"
    e.set_footer(text="아래 버튼으로 재고 충전, 가격 변경, 현황 확인을 진행하세요.")
    await interaction.channel.send(embed=e, view=StockPanelView())
    await interaction.response.send_message("재고/가격 패널을 전송했습니다!", ephemeral=True)


@bot.tree.command(name="재고", description="재고 및 가격 현황을 확인하고 빠르게 관리합니다 (관리자)")
@app_commands.default_permissions(administrator=True)
async def stock_quick(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
    await interaction.response.send_message(embed=stock_status_embed(), view=StockPanelView(), ephemeral=True)


@bot.tree.command(name="기록가져오기", description="구매 기록 채널의 메시지를 다시 분석해 DB에 반영합니다 (관리자)")
@app_commands.default_permissions(administrator=True)
async def import_history(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
    ch = interaction.client.get_channel(HISTORY_CHANNEL_ID)
    if ch is None:
        return await interaction.response.send_message("구매 기록 채널을 찾을 수 없습니다.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    found = []
    unmatched = []
    async with PURCHASE_LOCK:
        async for msg in ch.history(limit=None, oldest_first=True):
            if msg.author.bot:
                continue
            status, buyer, product, amount = parse_purchase(msg)
            if status == "ignore":
                continue
            if status != "ok":
                unmatched.append(msg.content.replace("`", "")[:60])
                continue
            found.append(
                (
                    str(buyer.id),
                    {
                        "product": product["name"],
                        "amount": amount,
                        "ts": int(msg.created_at.timestamp()),
                        "admin_id": msg.author.id,
                        "msg_id": msg.id,
                        "imported": True,
                    },
                )
            )

        data = load_data()
        added = dup = 0
        for uid, rec in found:
            hist = data["history"].setdefault(uid, [])
            if is_duplicate(hist, rec["msg_id"], rec["product"], rec["amount"], rec["ts"]):
                dup += 1
                continue
            hist.append(rec)
            added += 1
        for hist in data["history"].values():
            hist.sort(key=lambda h: h["ts"])
        save_data(data)

    e = discord.Embed(title="📥 구매 기록 가져오기 완료", color=GREEN)
    e.add_field(name="새로 추가", value=f"{added}건", inline=True)
    e.add_field(name="중복 제외", value=f"{dup}건", inline=True)
    e.add_field(name="인식 실패", value=f"{len(unmatched)}건", inline=True)
    if unmatched:
        sample = "\n".join(f"• `{t}`" for t in unmatched[:8])
        e.add_field(
            name="인식 불가 메시지 (일부)",
            value=sample + "\n\n제품명이 다른 경우 aliases 목록을 수정해 주세요.",
            inline=False,
        )
    e.set_footer(text="기록 가져오기는 잔액 및 재고에 영향을 주지 않습니다.")
    await interaction.followup.send(embed=e, ephemeral=True)


@bot.tree.command(name="잔액지급", description="유저에게 X를 직접 지급하거나 차감합니다 (관리자)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="대상 유저", amount="지급/차감할 X 수량 (차감은 음수)")
async def give_balance(interaction: discord.Interaction, user: discord.Member, amount: float):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)
    data = load_data()
    uid = str(user.id)
    data["balances"][uid] = round(max(0, data["balances"].get(uid, 0) + amount), 2)
    save_data(data)
    await interaction.response.send_message(
        f"{user.mention}님의 변경된 잔액: **{fmt_x(data['balances'][uid])}**", ephemeral=True
    )


@bot.event
async def on_ready():
    print(f"로그인 성공: {bot.user}")


bot.run(TOKEN)