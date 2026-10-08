# Carmei Zion Times for Home Assistant

The weekly prayer times of **Beit Knesset Carmei Zion** (בית כנסת כרמי ציון), Kiryat Gat, as Home Assistant sensors. They update automatically every week, as soon as the new schedule is published.

Every time on the weekly flyer becomes its own sensor, so you can run automations at, or a set time before, candle lighting, Mincha, Havdala and so on.

> Times are as printed on the shul's weekly schedule. Always double-check with the shul.

## Install

You need [HACS](https://hacs.xyz).

1. In Home Assistant, open **HACS**, then the **⋮** menu → **Custom repositories**.
2. Paste `https://github.com/ilan629/ha-carmei-zion`, choose type **Integration**, and click **Add**.
3. Search HACS for **Carmei Zion Times**, open it, and click **Download**.
4. **Restart Home Assistant**.
5. Go to **Settings → Devices & services → Add integration**, search for **Carmei Zion Times**, and press **Submit**. The feed address is already filled in.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ilan629&repository=ha-carmei-zion&category=integration)

## What you get

Everything sits under one device called **CZ**.

| Sensor | Example |
|---|---|
| `sensor.cz_friday_candle_lighting` | Candle lighting |
| `sensor.cz_friday_early_mincha`, `sensor.cz_friday_mincha`, `sensor.cz_friday_plag_hamincha`, `sensor.cz_friday_shkia` | Erev Shabbat |
| `sensor.cz_shabbat_shacharit_a` / `_b` / `_c`, `sensor.cz_shabbat_sof_zman_shma`, `sensor.cz_shabbat_mincha`, `sensor.cz_shabbat_maariv`, `sensor.cz_shabbat_kids_learning_1` / `_2`, `sensor.cz_shabbat_daf_yomi` | Shabbat |
| `sensor.cz_tzeit_shabbat` | Tzeit Shabbat / Havdala |
| `sensor.cz_sunday_shacharit_a` … `sensor.cz_friday_shacharit_b`, `sensor.cz_sunday_mincha` … `sensor.cz_thursday_maariv` | The weekday table: the next time that prayer happens on that day |
| `sensor.cz_parasha` | This week's parasha, with the full schedule as attributes |
| `binary_sensor.cz_schedule_up_to_date` | **Off** if this week's schedule hasn't come out yet |
| `sensor.cz_last_updated` | When the times were last downloaded (diagnostic) |

The time sensors are **timestamp** sensors, so you can use them directly as time triggers, including with an offset. Each one also has a `time` attribute such as `17:56` for dashboards. A sensor shows *unknown* when that row isn't on this week's flyer.

## Example automation

Turn on the Shabbat lights 20 minutes before candle lighting:

```yaml
automation:
  - alias: "Shabbat lights before candle lighting"
    triggers:
      - trigger: time
        at:
          entity_id: sensor.cz_friday_candle_lighting
          offset: "-00:20:00"
    actions:
      - action: light.turn_on
        target:
          entity_id: light.living_room
```

To show the exact time on a dashboard, use the `time` attribute or a template such as `{{ as_timestamp(states('sensor.cz_friday_mincha')) | timestamp_custom('%-H:%M') }}`.

## How it works, and what about Shabbat?

- Every hour, the integration downloads a small public file containing **only the times** from [ilan629.github.io/Carmei-Zion-Times](https://ilan629.github.io/Carmei-Zion-Times/). Nothing about your home is sent anywhere.
- The latest schedule is saved, so if your internet is down, or Home Assistant restarts on Shabbat without internet, your sensors keep this week's times.
- A failed or odd download never replaces good times. Test data is never used.
- Times are always Israel time, whatever time zone your Home Assistant is set to.

## Prefer a calendar?

Add the **Remote Calendar** integration with `https://ilan629.github.io/Carmei-Zion-Times/carmei-zion.ics` to get every prayer as a calendar event.

## Problems

Check `sensor.cz_last_updated`: its `last_problem` attribute says what went wrong with the latest download. You can also open an [issue](https://github.com/ilan629/ha-carmei-zion/issues).
