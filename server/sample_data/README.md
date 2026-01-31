# Sample data and seed mapping

Excel files in this directory are used by `scripts/seed_from_excel.py` to seed MongoDB.

## File → collection mapping

| File | Sheet | Collection(s) | Column mapping |
|------|--------|---------------|----------------|
| **Partners.xlsx** | result | stations | `id` → station_id, `latitude` + `longitude` → location string, name = "Station {id}", available_batteries = 0 |
| **Call Recording .xlsx** | Sheet1 | conversations, users | `Date` → start_time, `Calling No.` / `Name` → user_id; creates user per unique Calling No./Name |
| **ChargingEvents.xlsx** | result | swaps, users | `deviceId` → user_id, `date` / `ts` → date, station_id = first station or "unknown"; creates user per deviceId |
| **BatteryLogs.xlsx** | result | — | Not mapped to the 8-collection model (batteryId, occupant, isMisplaced, etc.). Optional future use. |

## Seed order

1. Stations (from Partners)
2. Agents (placeholder docs, no Excel)
3. Conversations (from Call Recording; creates users as needed)
4. Swaps (from ChargingEvents; creates users as needed; uses first station for station_id)

Run from server root:

```bash
uv run python -m scripts.seed_from_excel
uv run python -m scripts.seed_from_excel --drop   # drop collections then seed
```
