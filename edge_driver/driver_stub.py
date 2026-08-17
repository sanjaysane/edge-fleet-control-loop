"""
Placeholder for real sensor / router driver.

Replace with real I2C/SPI/BLE code. Secure boot verifies this file before import.

README: This is where "actual device driver" lives. Boot calls secure_boot.verify_artifact(__file__, __file__+'.sig') before loading.

If you have real hardware:
- init() opens bus, resets chip
- read() returns Measurement dict
- write() pushes config
- Versions immutable, rolled via OTA like app
"""
class DriverNotReady(Exception): pass

def init():
    # TODO(HW): open /dev/i2c-1, reset BME280 / BP cuff / Wi-Fi chip
    return {"status":"ok","driver_version":"v0.1-stub","hw":"sim"}

def read():
    # TODO(HW): replace fake vitals with real sensor read
    import random, time
    return {
      "ts": time.time(),
      "sys_mmHg": 118 + random.randint(-4,4),
      "dia_mmHg": 76 + random.randint(-3,3),
      "temp_c": 36.6 + random.random()*0.2,
      "note":"stub — replace with real driver"
    }

def write(cfg: dict):
    # TODO(HW): apply QoS, thresholds
    return {"applied": cfg}

# secure-boot shim: ensure this file would verify before import in prod agent
if __name__=="__main__":
    st=init()
    print(st)
    print(read())
