from Introduction.models import Player
import asyncio

async def run_job(player:Player):
    try:
        # Player fresh laden
        player.job_status = "running"
        await asyncio.sleep(300)
        player.job_status = "done"
        result = {"ok": True}
    except Exception as e:
        try:
            player = Player.objects.get(id=player_id)
            player.job_status = "failed"
        except:
            pass

        