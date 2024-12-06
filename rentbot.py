import discord
from discord.ext import commands
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.publickey import PublicKey
import asyncio
import time

# Bot konfiguráció
TOKEN = "MTMwOTkyOTExNDIwMjkzMTI2Mg.GWrebp.4Vz6lnNGvSrfIN__peSgxsuGNZXA1hkD8V4aLA"
RPC_URL = "https://api.devnet.solana.com"  # Devnet RPC
CHANNEL_ID = 1310698152927428629  # Ide írd annak a csatornának az ID-jét
ADMIN_CHANNEL_ID = 1310791509234155552  # Admin csatorna ID-ja
PUBLIC_CHANNEL_ID = 1310793783251701872  # Nyilvános csatorna ID

# Solana kliens
solana_client = Client(RPC_URL)

# Bot inicializálása
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Aktív bérlések tárolása
active_rentals = {}

# Sikeres tranzakciók naplózása
def log_successful_payment(wallet_address, private_key, user_name, amount):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open("C:/Users/Administrator/Desktop/solanabot/successful_payments.txt", "a") as f:
        f.write(f"{current_time} - User Name: {user_name}, "
                f"Wallet Address: {wallet_address}, Private Key: {private_key.hex()}, "
                f"Amount: {amount} SOL\n")
    print(f"Payment recorded for {user_name} - {amount} SOL.")

# Tárca exportálása fájlba
def export_wallet_to_txt(wallet_address, private_key):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open("C:/Users/Administrator/Desktop/solanabot/wallet_addresses_and_private_keys.txt", "a") as f:
        f.write(f"{current_time} - User Name: {active_rentals[wallet_address]['user_name']}, "
                f"Wallet Address: {wallet_address}, Private Key: {private_key.hex()}\n")
    print("Wallet address and private key have been exported to wallet_addresses_and_private_keys.txt")


# Fizetés ellenőrzése
async def check_payment(wallet_address, required_amount, interaction):
    expiration_time = active_rentals[wallet_address]["expires_at"]
    last_notified_balance = 0  # Nyomon követi az utoljára értesített egyenleget

    while True:
        try:
            if time.time() > expiration_time:
                await interaction.followup.send(
                    f"⏳ The payment link for wallet `{wallet_address}` has expired. "
                    "Please start a new transaction if you wish to proceed.",
                    ephemeral=True
                )
                del active_rentals[wallet_address]
                break

            response = solana_client.get_balance(PublicKey(wallet_address))
            balance = response['result']['value'] / 10**9  # Egyenleg SOL-ban

            if balance >= required_amount:
                print(f"**Payment received** on {wallet_address}: {balance} SOL")
                await interaction.followup.send(
                    f"✅ **Payment received successfully!**\n"
                    f"- **Wallet:** `{wallet_address}`\n"
                    f"- **Amount:** {balance} SOL\n\n"
                    "**The administrators have been notified about your rental request.** "
                    "**They will contact you within a few minutes to provide access to the node. 🛠️**",
                    ephemeral=True
                )
                log_successful_payment(wallet_address, active_rentals[wallet_address]["private_key"], interaction.user.name, balance)

                # Admin értesítés a tranzakcióról
                admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
                if admin_channel:
                    await admin_channel.send(
                        f"🔔 **NEW PAYMENT RECEIVED**\n"
                        f"\n"
                        f"**🇺🇸 NEW YORK NODE**\n"
                        f"- **User:** {interaction.user.name}\n"
                        f"- **Wallet Address:** `{wallet_address}`\n"
                        f"- **Amount:** {balance} SOL\n"
                        f"- **Private Key:** `{active_rentals[wallet_address]['private_key'].hex()}`\n"
                    )

                from discord import Embed

                # Nyilvános csatorna értesítés beágyazott formában ösztönző szöveggel
                public_channel = bot.get_channel(PUBLIC_CHANNEL_ID)
                if public_channel:
                    avatar_url = interaction.user.display_avatar.url
                    embed = Embed(
                        title="🌟 Node Rental Alert!",
                        description=(
                            f"{interaction.user.mention} just made an excellent choice by renting a node for "
                            f"**{active_rentals[wallet_address]['duration']}**! 🎉\n\n"
                            "🚀 Thank you for choosing **our service**! You're now part of an exclusive group of "
                            "visionaries who power the blockchain world. 🌍\n\n"
                            "If you have any questions or need assistance, feel free to reach out. "
                            "We're here to make sure your experience is nothing short of amazing! 🙌"
                        ),
                        color=0x00ff00  # Zöld szín
                    )
                    embed.set_thumbnail(url=avatar_url)  # Profilkép megjelenítése
                    embed.set_footer(
                        text=f"User: {interaction.user.name} • Thank you for choosing us!",
                        icon_url=avatar_url
                    )
    
                    await public_channel.send(embed=embed)


                del active_rentals[wallet_address]
                break

            elif balance > last_notified_balance and balance < required_amount:
                # Új értesítés minden részleges befizetésről
                missing_amount = required_amount - balance
                await interaction.followup.send(
                    f"⚠️ **Insufficient Payment**\n"
                    f"- **You sent:** {balance:.3f} SOL so far\n"
                    f"- **Required:** {required_amount:.3f} SOL\n"
                    f"- **Missing:** {missing_amount:.3f} SOL\n\n"
                    "**Please send the remaining amount to complete your transaction.**",
                    ephemeral=True
                )
                admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
                if admin_channel:
                    await admin_channel.send(
                        f"🚨 **LOW PAYMENT ALERT**\n"
                        f"- **User:** {interaction.user.name}\n"
                        f"- **Wallet Address:** `{wallet_address}`\n"
                        f"- **Amount Sent:** {balance:.3f} SOL\n"
                        f"- **Still Needed:** {missing_amount:.3f} SOL\n"
                    )
                last_notified_balance = balance  # Frissítjük az értesített egyenleget

        except Exception as e:
            print(f"Error checking payment: {e}")
            await asyncio.sleep(30)

        await asyncio.sleep(30)



# Free Trial gomb hozzáadása a meglévő RentView osztályhoz
class RentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_rent(self, interaction: discord.Interaction, duration: str, amount: float):
        new_wallet = Keypair()
        wallet_address = str(new_wallet.public_key)
        private_key = new_wallet.secret_key

        active_rentals[wallet_address] = {
            "user_name": interaction.user.name,
            "duration": duration,
            "amount": amount,
            "expires_at": time.time() + 15 * 60,
            "private_key": private_key
        }

        export_wallet_to_txt(wallet_address, private_key)

        await interaction.response.send_message(
            f"🇺🇸 NEW YORK\n"
            f"Please send **{amount} SOL** to the following **wallet address:** `{wallet_address}`\n"
            f"*Just a heads-up, the payment link will expire in 15 minutes* 🕒",
            ephemeral=True
        )

        await asyncio.create_task(check_payment(wallet_address, amount, interaction))

    @discord.ui.button(label="1 day - 0.2 SOL", style=discord.ButtonStyle.success)
    async def one_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rent(interaction, "1 day", 0.2)

    @discord.ui.button(label="1 week - 0.6 SOL", style=discord.ButtonStyle.success)
    async def one_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rent(interaction, "1 week", 0.6)

    @discord.ui.button(label="1 month - 1.5 SOL", style=discord.ButtonStyle.success)
    async def one_month(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rent(interaction, "1 month", 1.5)

    @discord.ui.button(label="Free Trial", style=discord.ButtonStyle.primary)
    async def free_trial(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "**🇺🇸 NEW YORK | 15 minutes Free Trial Information**\n"
            "To activate your free trial, please send a direct message (DM) to **@Duble ** or **@Owners**.\n\n"
            "⚠️ **Important Notes:**\n"
            "- The free trial is limited to **15 minutes**.\n"
            "- Only **one trial** per user is allowed.\n"
            "- **IP filtering** is enabled to prevent abuse.\n\n"
            "Enjoy exploring our services for a limited time! 🚀",
            ephemeral=True
        )

    @discord.ui.button(label="⏰ Extend Time", style=discord.ButtonStyle.danger)
    async def extend_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        wallet_address = next((address for address, data in active_rentals.items() if data["user_name"] == interaction.user.name), None)
        if wallet_address:
            active_rentals[wallet_address]["expires_at"] = time.time() + 15 * 60  # Új 15 perc hozzáadása
            await interaction.response.send_message(
                "⏳ Your transaction time has been extended by 15 minutes. Please complete your payment soon!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ No active transaction found. Please start a rental process first.",
                ephemeral=True
            )

# A bot elindulásakor közzéteszi a gombokat a megadott csatornában
@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        view = RentView()
        await channel.send(
            "**Choose your rental duration**\n"
            "\n"
            "**🇺🇸 NEW YORK**", view=view
        )

    print(f'Bot logged in as {bot.user}')


# Bot futtatása
bot.run(TOKEN)
