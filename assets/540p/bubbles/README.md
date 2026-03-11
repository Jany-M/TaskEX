# Bubble Templates

Upload 540p template images used by Auto-Bubble.

Preferred assets for 540p flow:
- use_btn.png
- ../dialogs/use_btn.png
- ../dialogs/cancel_btn.png

How Auto-Bubble now enters the flow:
- It first ensures the shared city/world-map starting screen used by other HUD-based features.
- It taps the first small status circle under the portrait in the top-left corner to open City Buff.
- It reads the Truce Agreement timer from the first card on that screen.
- If protection is low or missing, it taps the Truce Agreement row to enter the bubble choice screen.
- On the bubble choice screen, it targets rows by fixed order:
	- row 1 = 8h
	- row 2 = 24h
	- row 3 = 3d
	- row 4 = 7d (with one scroll)
	Then it checks the right-side action area.
- If the action area shows `Use`, it consumes inventory.
- If it shows a gem price instead, that row is purchase-only at the moment; the bot only taps it when `Allow buying bubble with gems` is enabled.
- After dialog confirmation, it verifies activation by reading the top banner remaining-time timer on Use Item.
- If a popup or accidental exit prompt appears during retreat, the flow cancels safely and continues (never quits the game).

Legacy fallback templates still supported:
- items_btn.png
- protection_tab.png

Template management is app-wide in Bot Manager > Bubbles tab.
Global shortcut is still available:
- Ctrl+Shift+B: open Bubble Template Configuration dialog

Per-bubble templates can still be configured and are used by legacy fallback flows.
