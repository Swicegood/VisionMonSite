import discord 

url = 'https://discord.com/api/webhooks/828356057680183377/VJLxRe7a0zzCmy6Q7LNVEy2qMD99yJLRARJ7RkYys5UQcY0yaO3HJFXbeM0Pox0FPMiA'

def send_discord(file,message,ttime):
    webhook = discord.Webhook.from_url(url, adapter=discord.RequestsWebhookAdapter())
    e = discord.Embed(description=ttime)
    if file:
        with open(file, "rb") as f:
            my_file = discord.File(f)
        webhook.send(message, username='Radha-Golokananda', file=my_file, embed=e)
    elif message:
        webhook.send(message, username='Radha-Golokananda', embed=e)
    else:
        return False