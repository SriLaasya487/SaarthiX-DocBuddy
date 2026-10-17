// DB-029: standard Bluetooth GATT health profiles via Web Bluetooth (Chrome on Android/desktop; not iOS Safari).
// Devices that use vendor-specific protocols are not covered - those need their own adapter.
const sfloat = (dv, o) => {
  const raw = dv.getUint16(o, true); let m = raw & 0x0fff, e = raw >> 12;
  if (m >= 0x0800) m -= 0x1000; if (e >= 0x08) e -= 0x10;
  return Math.round(m * 10 ** e * 100) / 100;
};
export const bleSupported = () => !!navigator.bluetooth;

function once(service, char, filters, parse, optional = []) {
  return new Promise(async (resolve, reject) => {
    try {
      const dev = await navigator.bluetooth.requestDevice({ filters: [{ services: [service] }], optionalServices: optional });
      const srv = await (await dev.gatt.connect()).getPrimaryService(service);
      const c = await srv.getCharacteristic(char);
      c.addEventListener("characteristicvaluechanged", (e) => { const r = parse(e.target.value); if (r) { dev.gatt.disconnect(); resolve({ device: dev.name || "", ...r }); } });
      await c.startNotifications();
      setTimeout(() => reject(new Error("No reading received. Start a measurement on the device.")), 60000);
    } catch (e) { reject(e); }
  });
}
export const readBloodPressure = () => once("blood_pressure", "blood_pressure_measurement", null, (dv) => {
  const kpa = dv.getUint8(0) & 1; let s = sfloat(dv, 1), d = sfloat(dv, 3);
  if (kpa) { s *= 7.50062; d *= 7.50062; }
  return { kind: "bp", value1: Math.round(s), value2: Math.round(d) };
});
export const readHeartRate = () => once("heart_rate", "heart_rate_measurement", null, (dv) => ({ kind: "pulse", value1: dv.getUint8(0) & 1 ? dv.getUint16(1, true) : dv.getUint8(1) }));
export const readSpO2 = () => once(0x1822, 0x2a5e, null, (dv) => ({ kind: "spo2", value1: Math.round(sfloat(dv, 1)) }));
export const readGlucose = () => once("glucose", "glucose_measurement", null, (dv) => {
  const f = dv.getUint8(0); let o = 10 + (f & 1 ? 2 : 0);
  if (!(f & 2)) return null;
  const v = sfloat(dv, o);
  return { kind: "sugar", value1: Math.round(f & 4 ? v * 18016 : v * 100000) };  // mol/L or kg/L -> mg/dL
}, ["battery_service"]);
