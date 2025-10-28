# === chart_unblocker.py ===
import os
from config import BOT_SETTINGS

# ⚠️ Update this path to your actual MetaTrader 5 Scripts folder!
MT5_SCRIPTS_PATH = r"C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\XXXX\MQL5\Scripts"

UNBLOCK_SCRIPT_TEMPLATE = '''\
//+------------------------------------------------------------------+
//|                      chart_unblocker.mq5                        |
//|           Auto-opens charts to force history download            |
//+------------------------------------------------------------------+
#property script_show_inputs

input string SymbolToLoad = "{symbol}";
input ENUM_TIMEFRAMES TF = PERIOD_M15;

void OnStart()
{{
   long chart = ChartOpen(SymbolToLoad, TF);
   if(chart > 0)
   {{
      Print("[UNBLOCK] Opened ", SymbolToLoad, " chart");
      ChartSetInteger(chart, CHART_AUTOSCROLL, false);
      for(int i = 0; i < 10; i++)
         ChartNavigate(chart, CHART_END, -100);
   }}
   else
   {{
      Print("[UNBLOCK][ERROR] Could not open chart for ", SymbolToLoad);
   }}
}}
'''

def write_unblock_scripts():
    if not os.path.exists(MT5_SCRIPTS_PATH):
        print(f"[ERROR] Script path not found: {MT5_SCRIPTS_PATH}")
        return

    for symbol in BOT_SETTINGS["symbols"]:
        filename = os.path.join(MT5_SCRIPTS_PATH, f"unblock_{symbol}.mq5")
        with open(filename, 'w') as f:
            f.write(UNBLOCK_SCRIPT_TEMPLATE.format(symbol=symbol))
        print(f"[✅] Script written: unblock_{symbol}.mq5")

if __name__ == '__main__':
    write_unblock_scripts()
