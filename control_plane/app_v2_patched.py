# Patcher note: integrate metrics middleware into app.py by adding:
# from metrics.middleware import track_rps, rps_counter, RPSCounter
# app.middleware("http")(track_rps)
#
# and adding endpoint:
# @app.get("/metrics")
# def metrics():
#   return {"rps": rps_counter.rps(), "devices": len(db["devices"])}
