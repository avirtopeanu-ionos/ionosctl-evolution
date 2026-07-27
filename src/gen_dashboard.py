#!/usr/bin/env python3
"""Generate a self-contained HTML dashboard from data.json (+cadence/journey/users).
Per-version charts are resampled client-side by a version selector (month step + left bound)."""
import json, os, subprocess
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(ROOT, "data")
IONOSCTL = os.environ.get("IONOSCTL_REPO", os.path.join(ROOT, "..", "workspace", "tools", "ionosctl"))
data = json.load(open(os.path.join(DATA, "data.json")))
def load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default
cadence = load("cadence.json", [])
journey = load("journey.json", [])
cfg     = load("config.json", {})
# Snap install base is owner-gated (not public). Only embed it into a local, gitignored
# dashboard when INCLUDE_SNAP=1; the committed dashboard.html never contains these numbers.
INCLUDE_SNAP = os.environ.get("INCLUDE_SNAP") == "1"
users   = load("users.json", []) if INCLUDE_SNAP else []

# default left bound = first commit by Alexandru (falls back to earliest data date)
try:
    first_commit = subprocess.run(
        ["git","-C",IONOSCTL,"log","--author=Virtopeanu",
         "--reverse","--format=%ad","--date=short"], capture_output=True, text=True).stdout.split("\n")[0].strip()
except Exception:
    first_commit = ""
DEF_MONTHS = cfg.get("months", 6)
DEF_STOP   = cfg.get("stop_date", first_commit or data[0]["date"])
# first release that includes Alexandru's work = earliest version dated >= first commit
FIRST_VER = next((r["version"] for r in data if first_commit and r["date"] >= first_commit), "")
FIRST_VER_DATE = next((r["date"] for r in data if r["version"] == FIRST_VER), "")
PRODUCTS = ["datacenter", "server", "lan", "k8s"]

DATA_JS = json.dumps(data); CAD_JS = json.dumps(cadence)
JRN_JS = json.dumps(journey); USR_JS = json.dumps(users)
f, l = data[0], data[-1]
def pct(a, b): return f"{'+' if b>=a else ''}{round((b-a)/a*100)}%"

jr = ""
if journey:
    jr = "<table class='jt'><tr><th></th><th>commands</th><th>keystrokes</th><th>wall-clock</th><th>wait mechanism</th></tr>"
    for r in journey:
        jr += f"<tr><td>{r['binary']}</td><td>{r['commands']}</td><td>{r['keystrokes']}</td><td>{r['wall_clock_s']}s</td><td><code>{r['wait_mechanism']}</code></td></tr>"
    jr += "</table>"

users_panel = ""
if users:
    users_panel = """<div class="panel"><h3>Snap Store install base</h3>
  <p>Devices with the ionosctl snap installed, sampled monthly from the Snap Store metrics API (publisher: ionos-cloud).</p>
  <canvas id="c_users"></canvas></div>"""

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ionosctl — Evolution 2021 → 2026</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{{--bg:#0b1020;--card:#151b31;--ink:#e8ecf7;--mut:#8b96b8;--acc:#4f9dff;--good:#31d0aa;--warn:#ffb454;--red:#ff6b8a;--grid:#232a44}}
  *{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(180deg,#0b1020,#0d1428);color:var(--ink);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}}
  .wrap{{max-width:1180px;margin:0 auto;padding:40px 24px 80px}}
  header h1{{font-size:34px;margin:0 0 6px;letter-spacing:-.5px}}
  header p{{color:var(--mut);margin:0 0 4px;font-size:16px}}
  .badge{{display:inline-block;background:var(--card);border:1px solid var(--grid);border-radius:999px;
    padding:4px 12px;color:var(--mut);font-size:13px;margin-top:10px}}
  h2.sec{{font-size:13px;letter-spacing:1.5px;text-transform:uppercase;color:var(--mut);
    margin:38px 0 2px;border-top:1px solid var(--grid);padding-top:26px}}
  .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:24px 0 10px}}
  .kpi{{background:var(--card);border:1px solid var(--grid);border-radius:16px;padding:20px}}
  .kpi .n{{font-size:30px;font-weight:700;letter-spacing:-.5px}}
  .kpi .d{{color:var(--mut);font-size:13px;margin-top:6px}}
  .kpi .delta{{font-size:13px;font-weight:600;margin-top:10px;display:inline-block;padding:2px 8px;border-radius:8px}}
  .up,.down{{color:var(--good);background:rgba(49,208,170,.12)}}
  .panel{{background:var(--card);border:1px solid var(--grid);border-radius:16px;padding:20px;margin-top:20px}}
  .panel h3{{margin:0 0 2px;font-size:16px}} .panel p{{margin:0 0 14px;color:var(--mut);font-size:13px}}
  canvas{{max-height:340px}}
  code{{color:#9fb4e0;background:rgba(79,157,255,.1);padding:1px 6px;border-radius:6px}}
  .ctl{{position:sticky;top:0;z-index:5;background:rgba(13,20,40,.92);backdrop-filter:blur(6px);
    border:1px solid var(--grid);border-radius:14px;padding:14px 18px;margin:24px 0 6px;display:flex;
    flex-wrap:wrap;gap:18px;align-items:center}}
  .ctl label{{font-size:13px;color:var(--mut);display:flex;flex-direction:column;gap:4px}}
  .ctl input{{background:#0c1226;border:1px solid var(--grid);color:var(--ink);border-radius:8px;padding:6px 9px;font:inherit;width:150px}}
  .ctl .rd{{margin-left:auto;color:var(--mut);font-size:13px}}
  .ctl b{{color:var(--ink)}}
  .capgrid{{display:flex;flex-direction:column;gap:6px;margin-top:6px}}
  .caprow{{display:grid;align-items:center;gap:6px}}
  .capname{{color:var(--ink);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .capcell{{height:22px;border-radius:5px}}
  .capcell.on{{background:var(--good)}} .capcell.off{{background:#1c2340;border:1px solid var(--grid)}}
  .caphdr .capcell{{background:transparent}} .caphv{{color:var(--mut);font-size:11px;text-align:center;height:auto}}
  table.jt{{width:100%;border-collapse:collapse;margin-top:6px;font-size:14px}}
  table.jt th,table.jt td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--grid)}}
  table.jt th{{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px}}
  footer{{color:var(--mut);font-size:12px;margin-top:40px;border-top:1px solid var(--grid);padding-top:18px}}
  @media(max-width:820px){{.kpis{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="wrap">
<header>
  <h1>ionosctl — 3.5 years of evolution</h1>
  <p>{f['date']} → {l['date']}. {len(data)} release binaries introspected offline, plus git history, code health and a live API journey{' and Snap install base' if users else ''}.</p>
  <span class="badge">{f['version']} → {l['version']} · Go {f['go_version']} → {l['go_version']}</span>
</header>

<div class="ctl">
  <label>Months between points
    <input id="m_step" type="number" min="1" max="36" step="1" value="{DEF_MONTHS}"></label>
  <label>Show back to (date)
    <input id="m_stop" type="date" value="{DEF_STOP}"></label>
  <button id="m_reset" style="align-self:flex-end;background:#0c1226;border:1px solid var(--grid);color:var(--ink);border-radius:8px;padding:7px 12px;cursor:pointer">Reset</button>
  <span class="rd" id="m_readout"></span>
</div>
{f'''<div style="color:var(--mut);font-size:12px;margin:2px 0 -6px"><span style="display:inline-block;width:22px;border-top:2px dashed #ff6b8a;vertical-align:middle;margin-right:6px"></span>first avirtopeanu contribution — <b style="color:var(--ink)">{FIRST_VER}</b> ({FIRST_VER_DATE[:7]}); shown on charts when the range reaches back before it</div>''' if FIRST_VER else ''}

<div class="kpis">
  <div class="kpi"><div class="n">{l['commands']}</div><div class="d">commands (was {f['commands']})</div>
    <span class="delta up">{pct(f['commands'],l['commands'])}</span></div>
  <div class="kpi"><div class="n">{l['bats']}</div><div class="d">integration test suites (was {f['bats']})</div>
    <span class="delta up">+{l['bats']-f['bats']}</span></div>
  <div class="kpi"><div class="n">{l['sdk_deps']}</div><div class="d">bundled IONOS API SDKs (was {f['sdk_deps']})</div>
    <span class="delta up">{pct(f['sdk_deps'],l['sdk_deps'])}</span></div>
  <div class="kpi"><div class="n">{l['contributors']}</div><div class="d">cumulative contributors (was {f['contributors']})</div>
    <span class="delta up">{pct(f['contributors'],l['contributors'])}</span></div>
</div>

<h2 class="sec">Growth &amp; reach</h2>
<div class="panel"><h3>Command count</h3>
  <p>Total commands and end-user (leaf) commands per release.</p>
  <canvas id="c_cmds"></canvas></div>
<div class="panel"><h3>APIs integrated and contributors</h3>
  <p>Bundled IONOS SDK modules (one per API wired into the CLI) and cumulative unique commit authors, per release.</p>
  <canvas id="c_sdk"></canvas></div>
{users_panel}

<h2 class="sec">Developer friction</h2>
<div class="panel"><h3>Lines of code per product</h3>
  <p>Command-layer lines of code implementing four representative products (files bucketed by path). Tracks how much code each product's commands take over time, across the file/dir restructures.</p>
  <canvas id="c_products"></canvas></div>
<div class="panel"><h3>Command count vs. code size, indexed</h3>
  <p>Both series scaled so the leftmost shown release = 100. Shows how command count and own-code size grew relative to that baseline.</p>
  <canvas id="c_divergence"></canvas></div>
<div class="panel"><h3>Code complexity</h3>
  <p>Functions with cyclomatic complexity over 15 (left axis) and mean cyclomatic complexity across all functions (right axis), vendor excluded.</p>
  <canvas id="c_health"></canvas></div>
<div class="panel"><h3>Duplication density</h3>
  <p>Duplicate code clone groups (dupl, threshold 60) per 10,000 own-code lines, per release.</p>
  <canvas id="c_dupl"></canvas></div>

<h2 class="sec">Capabilities &amp; UX</h2>
<div class="panel"><h3>Global capabilities available on every command</h3>
  <p>Flags usable on any command in that release. Filled = available. The global <code>--wait</code> is the clearest example: it is defined once and every command — including every future one — inherits it automatically, instead of each command re-implementing its own wait logic.</p>
  <div id="capgrid"></div></div>
<div class="panel"><h3>Flag surface</h3>
  <p>Total command-specific flags summed across all commands (excludes inherited global flags), per release.</p>
  <canvas id="c_flags"></canvas></div>

<h2 class="sec">Tests</h2>
<div class="panel"><h3>Unit and integration tests</h3>
  <p>Unit test files (<code>_test.go</code>) and BATs integration suites per release.</p>
  <canvas id="c_bats"></canvas></div>

<h2 class="sec">Release velocity</h2>
<div class="panel"><h3>Stable releases per quarter</h3>
  <p>Tagged stable releases (pre-releases excluded) grouped by calendar quarter, across all {sum(c['releases'] for c in cadence) if cadence else 0} releases. Not affected by the version selector.</p>
  <canvas id="c_cadence"></canvas></div>

<h2 class="sec">Live API journey</h2>
<div class="panel"><h3>Create datacenter + LAN, waiting for readiness</h3>
  <p>Same journey against the oldest and newest binary via the live API. Command count and keystrokes are comparable — core compute was already ergonomic in 2021. The real change is <em>how</em> waiting works: old commands each hand-rolled their own <code>--wait-for-request</code> (request-level, duplicated code, added command by command); the new global <code>--wait</code> is defined once and every command — current and future — inherits it automatically, waiting for the resource to reach AVAILABLE state with a shared <code>--timeout</code>. It blocks longer here (22s vs 6s) because it guarantees more.</p>
  {jr}</div>

<footer>
  Reproducible: <code>make</code> rebuilds everything. <code>make full</code> builds all stable tags for the version selector. <code>make users</code> refreshes Snap install base. <code>make sprint</code> diffs HEAD vs ~3 weeks ago.
  Services count drops at v6.10 by design — products were grouped under <code>compute</code> for discoverability. Example coverage stayed ≈100% ({round(l['example_coverage']*100)}% of leaf commands ship usage examples).
</footer>
</div>
<script>
const D = {DATA_JS}, CAD = {CAD_JS}, JRN = {JRN_JS}, USR = {USR_JS};
const FIRST_COMMIT='{first_commit}', PRODUCTS={json.dumps(PRODUCTS)};
const ink='#e8ecf7',mut='#8b96b8',acc='#4f9dff',good='#31d0aa',warn='#ffb454',red='#ff6b8a',grid='#232a44';
Chart.defaults.color=mut; Chart.defaults.font.family='inherit';
const gc={{grid:{{color:grid}},ticks:{{color:mut}}}};
const base=(extra={{}})=>({{responsive:true,animation:{{duration:300}},plugins:{{legend:{{labels:{{color:ink,usePointStyle:true,boxWidth:8}}}}}},
  scales:{{x:{{...gc}},y:{{...gc,beginAtZero:true}}}},...extra}});
function fill(ctx,c){{const g=ctx.createLinearGradient(0,0,0,320);g.addColorStop(0,c+'55');g.addColorStop(1,c+'05');return g;}}

// vertical marker at Alexandru's first commit — drawn only when the shown range reaches before it
let CUR=[];
const fcPlugin={{id:'fc',afterDatasetsDraw(chart){{
  if(!FIRST_COMMIT||CUR.length<2) return;
  const dts=CUR.map(r=>parse(r.date)), fc=parse(FIRST_COMMIT);
  if(fc<=dts[0]||fc>dts[dts.length-1]) return;      // only if it falls inside the visible range
  let i=0; while(i<dts.length-1 && dts[i+1]<fc) i++;
  const x=chart.scales.x, p0=x.getPixelForValue(i), p1=x.getPixelForValue(Math.min(i+1,dts.length-1));
  const span=dts[i+1]-dts[i], frac=span?(fc-dts[i])/span:0, px=p0+frac*(p1-p0);
  const {{top,bottom}}=chart.chartArea, ctx=chart.ctx;
  ctx.save();
  ctx.strokeStyle=red; ctx.lineWidth=1.5; ctx.setLineDash([4,3]);
  ctx.beginPath(); ctx.moveTo(px,top); ctx.lineTo(px,bottom); ctx.stroke();
  ctx.setLineDash([]); ctx.fillStyle=red; ctx.font='10px sans-serif'; ctx.textAlign='left';
  ctx.fillText('avirtopeanu', px+4, top+10);
  ctx.restore();
}}}};

// ---- version selector: resample D by month step, from newest back to stop date ----
const DAY=86400000;
function parse(d){{const [y,m,day]=d.split('-').map(Number);return Date.UTC(y,m-1,day);}}
function resample(months, stopISO){{
  const stop=parse(stopISO), anchor=parse(D[D.length-1].date);
  const targets=[]; let t=anchor;
  while(t>=stop){{ targets.push(t); t-=months*30.44*DAY; }}
  if(targets[targets.length-1]>stop) targets.push(stop);
  const chosen=new Map();  // version -> row, dedup, keep closest pick
  for(const tg of targets){{
    let best=null,bd=Infinity;
    for(const r of D){{const rd=parse(r.date); if(rd<stop-DAY) continue; const dist=Math.abs(rd-tg); if(dist<bd){{bd=dist;best=r;}}}}
    if(best) chosen.set(best.version,best);
  }}
  return [...chosen.values()].sort((a,b)=>parse(a.date)-parse(b.date));
}}

let charts=[];
function destroy(){{charts.forEach(c=>c.destroy());charts=[];}}
function mk(id,cfg){{cfg.plugins=(cfg.plugins||[]).concat(fcPlugin);const c=new Chart(document.getElementById(id),cfg);charts.push(c);return c;}}
const line=(label,data,color,f=false)=>({{label,data,borderColor:color,backgroundColor:f?(ctx=>fill(ctx.chart.ctx,color)):undefined,fill:f,tension:.35,pointRadius:2}});

function render(S){{
  destroy(); CUR=S;
  const L=S.map(r=>r.version+' · '+r.date.slice(0,7));
  mk('c_cmds',{{type:'line',data:{{labels:L,datasets:[
    line('Total commands',S.map(r=>r.commands),acc,true),
    line('End-user commands',S.map(r=>r.leaf_commands),good)]}},options:base()}});
  mk('c_sdk',{{type:'line',data:{{labels:L,datasets:[
    line('Bundled API SDKs',S.map(r=>r.sdk_deps),acc,true),
    line('Contributors',S.map(r=>r.contributors),warn)]}},options:base()}});
  const PCOL={{datacenter:acc,server:good,lan:warn,k8s:red}};
  mk('c_products',{{type:'line',data:{{labels:L,datasets:PRODUCTS.map(p=>
    line(p,S.map(r=>r.product_loc[p]),PCOL[p]))}},options:base()}});
  const b0c=S[0].commands,b0l=S[0].own_loc;
  mk('c_divergence',{{type:'line',data:{{labels:L,datasets:[
    line('Commands (indexed)',S.map(r=>Math.round(r.commands/b0c*1000)/10),acc,true),
    line('Own-code lines (indexed)',S.map(r=>Math.round(r.own_loc/b0l*1000)/10),warn)]}},
    options:base({{scales:{{x:{{...gc}},y:{{...gc,beginAtZero:false,title:{{display:true,text:'leftmost = 100',color:mut}}}}}}}})}});
  mk('c_health',{{type:'line',data:{{labels:L,datasets:[
    {{...line('Functions over complexity 15',S.map(r=>r.cyclo_over15),red),yAxisID:'y'}},
    {{...line('Mean complexity',S.map(r=>r.gocyclo_avg),acc),yAxisID:'y1'}}]}},
    options:base({{scales:{{x:{{...gc}},y:{{...gc,position:'left',title:{{display:true,text:'count over 15',color:mut}}}},
      y1:{{...gc,position:'right',grid:{{drawOnChartArea:false}},beginAtZero:false,title:{{display:true,text:'mean',color:mut}}}}}}}})}});
  mk('c_dupl',{{type:'line',data:{{labels:L,datasets:[line('Clone groups per 10k LOC',S.map(r=>r.clones_per_10k),warn,true)]}},
    options:base({{plugins:{{legend:{{display:false}}}},scales:{{x:{{...gc}},y:{{...gc,beginAtZero:false}}}}}})}});
  mk('c_flags',{{type:'line',data:{{labels:L,datasets:[line('Command-specific flags (total)',S.map(r=>r.own_flag_total),acc,true)]}},
    options:base({{plugins:{{legend:{{display:false}}}}}})}});
  mk('c_bats',{{type:'bar',data:{{labels:L,datasets:[
    {{label:'Unit test files',data:S.map(r=>r.unit_test_files),backgroundColor:warn+'cc',borderRadius:4,stack:'t'}},
    {{label:'Integration suites (BATs)',data:S.map(r=>r.bats),backgroundColor:good+'cc',borderRadius:4,stack:'t'}}]}},
    options:base({{scales:{{x:{{...gc,stacked:true}},y:{{...gc,stacked:true}}}}}})}});
  buildCapGrid(S);
  document.getElementById('m_readout').innerHTML='showing <b>'+S.length+'</b> of '+D.length+' releases';
}}

// capability presence grid (columns = selected versions)
const CAPS=[['wait','Wait for ready — --wait'],['query_jmespath','JMESPath query — --query'],
  ['pagination','Pagination — --limit/--offset'],['filters','Server-side filters — --filters'],
  ['order_by','Order results — --order-by'],['depth','Response depth — --depth'],
  ['no_headers','Scriptable output — --no-headers'],['cols','Column selection — --cols']];
function buildCapGrid(S){{
  const cols='250px repeat('+S.length+',1fr)';
  let h='<div class="capgrid"><div class="caprow caphdr" style="grid-template-columns:'+cols+'"><div class="capname"></div>'+
    S.map(r=>'<div class="capcell caphv">'+r.version.replace('v','')+'</div>').join('')+'</div>';
  for(const [k,name] of CAPS){{
    h+='<div class="caprow" style="grid-template-columns:'+cols+'"><div class="capname">'+name+'</div>'+
      S.map(r=>'<div class="capcell '+(r.cap_detail[k]?'on':'off')+'"></div>').join('')+'</div>';
  }}
  h+='</div>'; document.getElementById('capgrid').innerHTML=h;
}}

// independent charts (not resampled)
new Chart(c_cadence,{{type:'bar',data:{{labels:CAD.map(c=>c.quarter),datasets:[
  {{label:'Releases',data:CAD.map(c=>c.releases),backgroundColor:acc+'cc',borderRadius:4}}]}},
  options:base({{plugins:{{legend:{{display:false}}}}}})}});
if(USR.length && document.getElementById('c_users')) new Chart(c_users,{{type:'line',data:{{labels:USR.map(u=>u.date.slice(0,7)),datasets:[
  {{label:'Snap devices',data:USR.map(u=>u.users),borderColor:good,backgroundColor:ctx=>fill(ctx.chart.ctx,good),fill:true,tension:.35,pointRadius:2}}]}},
  options:base({{plugins:{{legend:{{display:false}}}}}})}});

// wire controls
const mStep=document.getElementById('m_step'), mStop=document.getElementById('m_stop');
function apply(){{ let m=Math.max(1,parseInt(mStep.value)||{DEF_MONTHS}); render(resample(m, mStop.value||'{DEF_STOP}')); }}
mStep.addEventListener('input',apply); mStop.addEventListener('change',apply);
document.getElementById('m_reset').addEventListener('click',()=>{{mStep.value={DEF_MONTHS};mStop.value='{DEF_STOP}';apply();}});
apply();
</script></body></html>"""

out = os.path.join(ROOT, "dashboard.local.html" if INCLUDE_SNAP else "dashboard.html")
open(out, "w").write(html)
print("wrote", out, f"({len(html)} bytes) · default step={DEF_MONTHS}mo stop={DEF_STOP} · users={len(users)} pts")
