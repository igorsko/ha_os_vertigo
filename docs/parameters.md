# Observed parameter map

Tuya protocol 3.3. This profile covers the examined OS Home Vertigo variant only; do not apply it blindly to other models.

| DP | OS Home schema code | Type | Meaning |
|---|---|---|---|
| 1 | Power | boolean | Master power |
| 2 | WindSpeed | string enum 1–9 | Fan speed |
| 3 | Windmode | string enum close/sleep/heavy/fresh | Normal/Sleep/Turbo/Fresh |
| 8 | Windleftright | boolean | Horizontal oscillation |
| 9 | TempSet | integer 1–30 | Target temperature, °C, step 1 |
| 10 | NowTemp | integer, read only | Ambient temperature, °C |
| 11 | Timer | string enum 0–8 | Disabled / 1–8 hours |
| 12 | Countdown | integer, read only | Remaining minutes |
| 13 | fault | bitmap, read only | Raw fault code; bit meanings unknown |
| 102 | voice | boolean | Acoustic signal; false = silent |
| 103 | warm_switch | boolean | Heating enabled |
| 106 | warm_speed | string enum 1–4 | Heating level |
| 107 | UVC | boolean | UV lamp |

The thermostat joins DP 9 and DP 10. Heating mode enables master power and DP 103; OFF writes only DP 103=false. No thermostat action or electrical-power estimate is synthesized because the schema does not establish those measurements.

Temperature must be a whole number on the wire: a generic float payload was not accepted in the earlier LocalTuya configuration. The standalone component validates ranges and sends integer targets.
