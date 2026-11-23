#!/usr/bin/env python3
"""Build docs/web/journey.html: the history of the GENESIS workspace.

Reads git from the sibling repos (infra, apex, exhib, glob, thyme, omni) and
every version of infra's ROADMAP.md, and writes one self-contained HTML page
(no build step, no network). Run from anywhere:

    python3 scripts/journey.py
"""

import json
import os
import re
import subprocess
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
INFRA = os.path.dirname(HERE)
ROOT = os.path.dirname(INFRA)
OUT = os.path.join(INFRA, "docs", "web", "journey.html")
REPOS = ["infra", "apex", "exhib", "glob", "thyme", "omni"]
ROLE = {
    "infra": "Talos cluster, Flux, every app",
    "apex": "0xbf.ch: Ratatui site, WASM app, SSH TUI",
    "exhib": "glry.0xbf.ch: Hugo gallery + processor",
    "glob": "blg.0xbf.ch: Typst blog",
    "thyme": "Typst static-site package (Universe)",
    "omni": "nix: machines, home, devil VM",
}


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", os.path.join(ROOT, repo), *args], capture_output=True, text=True
    ).stdout


def collect():
    commits, tags, merges = [], [], {}
    for repo in REPOS:
        if not os.path.isdir(os.path.join(ROOT, repo, ".git")):
            continue
        log = git(repo, "log", "--all", "--no-merges", "--date=iso-strict",
                  "--pretty=format:@@%H|%ad|%s", "--numstat")
        cur = None
        for line in log.splitlines():
            if line.startswith("@@"):
                h, d, s = line[2:].split("|", 2)
                cur = {"r": repo, "h": h[:8], "d": d, "s": s, "a": 0, "x": 0, "f": 0}
                commits.append(cur)
            elif line.strip() and cur:
                parts = line.split("\t")
                if len(parts) == 3:
                    cur["a"] += int(parts[0]) if parts[0].isdigit() else 0
                    cur["x"] += int(parts[1]) if parts[1].isdigit() else 0
                    cur["f"] += 1
        merges[repo] = len(git(repo, "log", "--all", "--merges", "--pretty=format:%h").splitlines())
        for t in git(repo, "for-each-ref", "--sort=creatordate",
                     "--format=%(refname:short)|%(creatordate:iso-strict)|%(contents:subject)",
                     "refs/tags").splitlines():
            if t:
                name, d, s = (t.split("|", 2) + ["", ""])[:3]
                tags.append({"r": repo, "t": name, "d": d, "s": s})
    # Every version of the roadmap: open and done counts, and when each done
    # item first appeared.
    roadmap, first_done = [], OrderedDict()
    for line in reversed(git("infra", "log", "--date=iso-strict",
                             "--pretty=format:%H|%ad|%s", "--", "ROADMAP.md").splitlines()):
        h, d, s = line.split("|", 2)
        body = git("infra", "show", f"{h}:ROADMAP.md")
        done = [re.sub(r"^\s*- \[x\]\s*", "", l).strip() for l in body.splitlines() if re.match(r"^\s*- \[x\]", l)]
        todo = [l for l in body.splitlines() if re.match(r"^\s*- \[ \]", l)]
        for item in done:
            key = re.sub(r"\s+", " ", item)
            first_done.setdefault(key, d)
        # Done = distinct items ticked so far (the file gets reorganized, so the
        # count in one version can drop without work being undone).
        roadmap.append({"d": d, "s": s, "done": len(first_done), "open": len(todo)})
    done_items = [{"d": d, "t": t} for t, d in first_done.items()]
    commits.sort(key=lambda c: c["d"])
    return {"repos": REPOS, "role": ROLE, "commits": commits, "tags": tags,
            "merges": merges, "roadmap": roadmap, "done": done_items}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GENESIS journey</title>
<style>
:root{--bg:#fcfcfb;--panel:#ffffff;--line:#e4e4e0;--fg:#1d1d1b;--muted:#5f5f5a;--dim:#8d8d86;--grid:#ececE8;
 --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;
 --q1:#e5f0fc;--q2:#b7d3f5;--q3:#7fb0ec;--q4:#4a8fe0;--q5:#2a78d6;--q6:#1a5aa8;--r:10px;
 --mono:ui-monospace,SFMono-Regular,Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--panel:#222220;--line:#34342f;--fg:#ecece8;--muted:#a9a9a2;--dim:#7c7c75;--grid:#2c2c28;
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#0ca30c;
 --q1:#1f2a38;--q2:#1d3a5f;--q3:#22548d;--q4:#2c6fbd;--q5:#3987e5;--q6:#79adf0}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:28px;margin:0 0 4px} h2{font-size:18px;margin:36px 0 6px} .lead{color:var(--muted);margin:0 0 14px}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}@media(max-width:700px){.tiles{grid-template-columns:repeat(2,1fr)}}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:12px 14px}
.tile .n{font-size:26px;font-weight:650;font-variant-numeric:tabular-nums} .tile .l{color:var(--muted);font-size:12.5px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:14px;position:relative}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12.5px;color:var(--muted);margin:2px 0 10px}
.legend button{all:unset;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.legend button[aria-pressed=false]{opacity:.35} .sw{width:10px;height:10px;border-radius:3px;display:inline-block}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 10px}
.row button,.row input,.row select{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:5px 10px;font:inherit;font-size:12.5px}
.row button[aria-pressed=true]{border-color:var(--fg)}
svg text{fill:var(--muted);font-size:11px;font-family:system-ui,sans-serif}
.tip{position:fixed;pointer-events:none;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12.5px;box-shadow:0 6px 24px #0003;display:none;z-index:9;max-width:340px}
.tip b{font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px} th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px} td.num{text-align:right;font-variant-numeric:tabular-nums}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px} @media(max-width:900px){.two{grid-template-columns:1fr}}
.log{max-height:520px;overflow:auto} .mono{font-family:var(--mono);font-size:12px}
.tl{border-left:2px solid var(--line);margin-left:6px;padding-left:16px}
.tl .ev{position:relative;margin:0 0 10px} .tl .ev::before{content:"";position:absolute;left:-22px;top:6px;width:10px;height:10px;border-radius:50%;background:var(--panel);border:2px solid var(--muted)}
.tl .d{color:var(--dim);font-size:12px;font-variant-numeric:tabular-nums}
.hidden{display:none}
</style>
</head>
<body>
<main>
<h1>GENESIS journey</h1>
<p class="lead" id="sub"></p>
<div class="tiles" id="tiles"></div>

<h2>Activity per day</h2>
<p class="lead">Commits per day, stacked by repository. Click a legend entry to hide a repo. Hover a bar for the day.</p>
<div class="card">
 <div class="row"><span>Measure</span><button data-m="c" aria-pressed="true">commits</button><button data-m="l" aria-pressed="false">lines changed</button><span style="flex:1"></span><button id="tbl1" aria-pressed="false">table</button></div>
 <div class="legend" id="leg"></div>
 <div id="daily"></div><div id="dailyTable" class="hidden log"></div>
</div>

<div class="two">
 <div><h2>Calendar</h2><p class="lead">Commits per day, darker = more. All repos.</p><div class="card"><div id="cal"></div></div></div>
 <div><h2>When</h2><p class="lead">Commits by weekday and hour (local time of the commit).</p><div class="card"><div id="week"></div></div></div>
</div>

<h2>Repositories</h2>
<p class="lead">Volume per repo. Lines are insertions and deletions from <span class="mono">git log --numstat</span>, including generated and vendored files.</p>
<div class="card"><div id="repoTable"></div></div>

<h2>Roadmap</h2>
<p class="lead">Every committed version of <span class="mono">ROADMAP.md</span>: open items, and distinct items done so far. Hover for the commit.</p>
<div class="card"><div id="road"></div></div>

<div class="two">
 <div><h2>Everything done</h2><p class="lead">Each item the roadmap ever ticked, at the first version that ticked it.</p><div class="card log"><div class="tl" id="done"></div></div></div>
 <div><h2>Releases</h2><p class="lead">Tags across repos, newest first.</p><div class="card log"><div class="row"><select id="tagRepo"></select></div><div class="tl" id="tags"></div></div></div>
</div>

<h2>Commit log</h2>
<div class="card"><div class="row"><input id="q" placeholder="search subjects" size="30"><select id="logRepo"></select><span id="logCount" style="color:var(--muted)"></span></div><div class="log" id="log"></div></div>
</main>
<div class="tip" id="tip"></div>
<script>
const DATA = __DATA__;
const $=s=>document.querySelector(s), NS="http://www.w3.org/2000/svg";
const el=(t,a={},p)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.append(e);return e};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const color=r=>`var(--s${DATA.repos.indexOf(r)+1})`;
const day=d=>d.slice(0,10), fmt=n=>n.toLocaleString("en");
const tip=$("#tip");
function showTip(e,html){tip.innerHTML=html;tip.style.display="block";const w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.min(innerWidth-w-8,e.clientX+14)+"px";tip.style.top=Math.max(8,e.clientY-h-12)+"px"}
const hideTip=()=>tip.style.display="none";

// ---------- summary
const C=DATA.commits, days=[...new Set(C.map(c=>day(c.d)))].sort();
const first=days[0], last=days[days.length-1];
const span=Math.round((new Date(last)-new Date(first))/864e5)+1;
const adds=C.reduce((s,c)=>s+c.a,0), dels=C.reduce((s,c)=>s+c.x,0);
const merges=Object.values(DATA.merges).reduce((a,b)=>a+b,0);
$("#sub").textContent=`${first} to ${last} · ${DATA.repos.length} repositories · generated from git`;
const tiles=[[fmt(C.length),"commits"],[fmt(days.length)+" / "+span,"active days / calendar days"],[(C.length/days.length).toFixed(1),"commits per active day"],
 [fmt(merges),"merged pull requests"],[fmt(DATA.tags.length),"tags (releases)"],["+"+fmt(adds),"lines added"],["−"+fmt(dels),"lines removed"],[fmt(DATA.done.length),"roadmap items done"]];
$("#tiles").innerHTML=tiles.map(([n,l])=>`<div class="tile"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");

// ---------- daily stacked bars
const allDays=[];for(let t=new Date(first);t<=new Date(last);t=new Date(+t+864e5))allDays.push(t.toISOString().slice(0,10));
const per={};for(const d of allDays)per[d]=Object.fromEntries(DATA.repos.map(r=>[r,{c:0,l:0}]));
for(const c of C){const p=per[day(c.d)][c.r];p.c++;p.l+=c.a+c.x}
const on=new Set(DATA.repos);let measure="c";
$("#leg").innerHTML=DATA.repos.map(r=>`<button aria-pressed="true" data-r="${r}"><span class="sw" style="background:${color(r)}"></span>${r}</button>`).join("");
$("#leg").onclick=e=>{const b=e.target.closest("button");if(!b)return;const r=b.dataset.r;on.has(r)?on.delete(r):on.add(r);b.setAttribute("aria-pressed",on.has(r));drawDaily()};
document.querySelectorAll("[data-m]").forEach(b=>b.onclick=()=>{measure=b.dataset.m;document.querySelectorAll("[data-m]").forEach(x=>x.setAttribute("aria-pressed",x===b));drawDaily()});
$("#tbl1").onclick=e=>{const t=$("#dailyTable").classList.toggle("hidden");e.target.setAttribute("aria-pressed",!t);$("#daily").classList.toggle("hidden",!t)};
function niceMax(v){if(v<=0)return 5;const st=niceStep(v/5);return Math.ceil(v/st)*st}
function niceStep(v){const p=10**Math.floor(Math.log10(v)),m=v/p;return (m<=1?1:m<=2?2:m<=5?5:10)*p}
function drawDaily(){
 const box=$("#daily");box.innerHTML="";const W=box.clientWidth||1100,H=260,L=44,B=24,T=8,R=6;
 const svg=el("svg",{width:W,height:H,viewBox:`0 0 ${W} ${H}`},box);
 const tot=d=>DATA.repos.filter(r=>on.has(r)).reduce((s,r)=>s+per[d][r][measure],0);
 const max=niceMax(Math.max(1,...allDays.map(tot)));const bw=(W-L-R)/allDays.length;
 const st=niceStep(max/5);for(let v=0;v<=max+1e-9;v+=st){const y=H-B-(H-B-T)*v/max;el("line",{x1:L,x2:W-R,y1:y,y2:y,stroke:"var(--grid)"},svg);el("text",{x:L-6,y:y+4,"text-anchor":"end"},svg).textContent=fmt(Math.round(v))}
 allDays.forEach((d,i)=>{let y=H-B;const x=L+i*bw+1,w=Math.max(1,bw-2);
  const segs=DATA.repos.filter(r=>on.has(r)&&per[d][r][measure]>0);
  segs.forEach((r,k)=>{const h=(H-B-T)*per[d][r][measure]/max;const top=k===segs.length-1;
   const g=Math.max(.5,h>2&&k>0?h-2:h),yt=y-h,rr=top?Math.min(4,w/2,g):0;
   el("path",{d:`M${x},${yt+g}V${yt+rr}Q${x},${yt} ${x+rr},${yt}H${x+w-rr}Q${x+w},${yt} ${x+w},${yt+rr}V${yt+g}Z`,fill:color(r)},svg);y-=h});
  if(i%7===0)el("text",{x:x+w/2,y:H-6,"text-anchor":"middle"},svg).textContent=d.slice(5);
  const hit=el("rect",{x:L+i*bw,y:T,width:bw,height:H-B-T,fill:"transparent"},svg);
  hit.onmousemove=e=>{const rows=DATA.repos.filter(r=>per[d][r][measure]>0).map(r=>`<div><span class="sw" style="background:${color(r)}"></span> ${r} <b>${fmt(per[d][r][measure])}</b></div>`).join("")||"<div>no commits</div>";
   showTip(e,`<div><b>${d}</b> · ${fmt(tot(d))} ${measure==="c"?"commits":"lines"}</div>${rows}`)};hit.onmouseleave=hideTip});
 $("#dailyTable").innerHTML=`<table><tr><th>day</th>${DATA.repos.map(r=>`<th>${r}</th>`).join("")}<th>total</th></tr>${allDays.filter(d=>tot(d)>0).reverse().map(d=>`<tr><td class="mono">${d}</td>${DATA.repos.map(r=>`<td class="num">${per[d][r][measure]||""}</td>`).join("")}<td class="num">${fmt(tot(d))}</td></tr>`).join("")}</table>`;
}

// ---------- calendar (sequential blue)
function drawCal(){
 const box=$("#cal");const cnt={};for(const c of C)cnt[day(c.d)]=(cnt[day(c.d)]||0)+1;
 const start=new Date(first);start.setDate(start.getDate()-((start.getDay()+6)%7));
 const weeks=Math.ceil((new Date(last)-start)/864e5/7)+1,cs=15,L=28,T=18;
 const svg=el("svg",{width:L+weeks*cs+4,height:T+7*cs+4},box);const max=Math.max(...Object.values(cnt));
 const step=v=>v===0?"var(--grid)":`var(--q${Math.min(6,1+Math.ceil(5*v/max))})`;
 ["Mon","","Wed","","Fri","",""].forEach((t,i)=>{if(t)el("text",{x:0,y:T+i*cs+11},svg).textContent=t});
 for(let w=0;w<weeks;w++)for(let k=0;k<7;k++){const t=new Date(+start+(w*7+k)*864e5),d=t.toISOString().slice(0,10);if(d<first||d>last)continue;
  if(t.getDate()<=7&&k===0)el("text",{x:L+w*cs,y:11},svg).textContent=t.toLocaleString("en",{month:"short"});
  const v=cnt[d]||0;const r=el("rect",{x:L+w*cs,y:T+k*cs,width:cs-3,height:cs-3,rx:3,fill:step(v)},svg);
  r.onmousemove=e=>showTip(e,`<b>${d}</b> · ${v} commits`);r.onmouseleave=hideTip}
}

// ---------- weekday x hour
function drawWeek(){
 const box=$("#week");const g=Array.from({length:7},()=>Array(24).fill(0));
 for(const c of C){const m=c.d.match(/T(\d\d)/);const wd=(new Date(c.d.slice(0,10)+"T12:00:00").getDay()+6)%7;g[wd][+m[1]]++}
 const cs=17,L=34,T=14,svg=el("svg",{width:L+24*cs+4,height:T+7*cs+18},box);const max=Math.max(...g.flat());
 const names=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
 names.forEach((n,i)=>el("text",{x:0,y:T+i*cs+12},svg).textContent=n);
 for(let h=0;h<24;h+=3)el("text",{x:L+h*cs,y:T+7*cs+13},svg).textContent=String(h).padStart(2,"0");
 g.forEach((row,i)=>row.forEach((v,h)=>{const r=el("rect",{x:L+h*cs,y:T+i*cs,width:cs-3,height:cs-3,rx:3,fill:v?`var(--q${Math.min(6,1+Math.ceil(5*v/max))})`:"var(--grid)"},svg);
  r.onmousemove=e=>showTip(e,`<b>${names[i]} ${String(h).padStart(2,"0")}:00</b> · ${v} commits`);r.onmouseleave=hideTip}));
}

// ---------- repo table
function drawRepos(){
 const rows=DATA.repos.map(r=>{const cs=C.filter(c=>c.r===r);const ds=[...new Set(cs.map(c=>day(c.d)))];
  return{r,n:cs.length,days:ds.length,a:cs.reduce((s,c)=>s+c.a,0),x:cs.reduce((s,c)=>s+c.x,0),first:cs.length?day(cs[0].d):"-",last:cs.length?day(cs[cs.length-1].d):"-",tags:DATA.tags.filter(t=>t.r===r).length,prs:DATA.merges[r]||0}});
 const max=Math.max(...rows.map(x=>x.n));
 $("#repoTable").innerHTML=`<table><tr><th>repo</th><th>what</th><th>commits</th><th class="num">active days</th><th class="num">PRs</th><th class="num">tags</th><th class="num">+lines</th><th class="num">−lines</th><th>first</th><th>last</th></tr>${rows.map(x=>`<tr><td><span class="sw" style="background:${color(x.r)}"></span> <b>${x.r}</b></td><td style="color:var(--muted)">${esc(DATA.role[x.r]||"")}</td><td><svg width="120" height="12"><rect x="0" y="1" height="10" rx="3" width="${Math.max(2,110*x.n/max)}" fill="${color(x.r)}"/></svg> <span class="mono">${x.n}</span></td><td class="num">${x.days}</td><td class="num">${x.prs}</td><td class="num">${x.tags}</td><td class="num">${fmt(x.a)}</td><td class="num">${fmt(x.x)}</td><td class="mono">${x.first}</td><td class="mono">${x.last}</td></tr>`).join("")}</table>`;
}

// ---------- roadmap lines (one axis: item counts)
function drawRoad(){
 const box=$("#road");const R=DATA.roadmap;if(!R.length)return;const W=box.clientWidth||1100,H=220,L=40,B=24,T=10,Rt=60;
 const svg=el("svg",{width:W,height:H},box);const max=niceMax(Math.max(...R.map(v=>Math.max(v.done,v.open))));
 const t0=+new Date(R[0].d),t1=+new Date(R[R.length-1].d)||t0+1;const X=d=>L+(W-L-Rt)*((+new Date(d)-t0)/Math.max(1,t1-t0)),Y=v=>H-B-(H-B-T)*v/max;
 const st=niceStep(max/5);for(let v=0;v<=max+1e-9;v+=st){el("line",{x1:L,x2:W-Rt,y1:Y(v),y2:Y(v),stroke:"var(--grid)"},svg);el("text",{x:L-6,y:Y(v)+4,"text-anchor":"end"},svg).textContent=Math.round(v)}
 [["done","var(--s3)"],["open","var(--s2)"]].forEach(([k,c])=>{el("path",{d:R.map((v,i)=>(i?"L":"M")+X(v.d)+","+Y(v[k])).join(""),fill:"none",stroke:c,"stroke-width":2},svg);
  const lv=R[R.length-1];el("text",{x:X(lv.d)+6,y:Y(lv[k])+4,style:"fill:var(--fg)"},svg).textContent=`${k} ${lv[k]}`});
 for(let k=0;k<=6;k++){const t=new Date(t0+(t1-t0)*k/6).toISOString().slice(0,10);el("text",{x:X(t+"T12:00:00Z"),y:H-6,"text-anchor":"middle"},svg).textContent=t.slice(5)}
 const cross=el("line",{y1:T,y2:H-B,stroke:"var(--dim)","stroke-dasharray":"3 3",visibility:"hidden"},svg);
 const hit=el("rect",{x:L,y:T,width:W-L-Rt,height:H-B-T,fill:"transparent"},svg);
 hit.onmousemove=e=>{const bx=svg.getBoundingClientRect().left;const x=e.clientX-bx;let best=R[0];for(const v of R)if(Math.abs(X(v.d)-x)<Math.abs(X(best.d)-x))best=v;
  cross.setAttribute("x1",X(best.d));cross.setAttribute("x2",X(best.d));cross.setAttribute("visibility","visible");
  showTip(e,`<div><b>${best.d.slice(0,16).replace("T"," ")}</b></div><div>${esc(best.s)}</div><div><span class="sw" style="background:var(--s3)"></span> done <b>${best.done}</b> · <span class="sw" style="background:var(--s2)"></span> open <b>${best.open}</b></div>`)};
 hit.onmouseleave=()=>{hideTip();cross.setAttribute("visibility","hidden")};
}

// ---------- done items, tags, log
function drawDone(){$("#done").innerHTML=[...DATA.done].reverse().map(x=>`<div class="ev"><div class="d">${day(x.d)}</div><div>${esc(x.t.replace(/\*\*/g,""))}</div></div>`).join("")}
function drawTags(){const sel=$("#tagRepo");sel.innerHTML=`<option value="">all repos</option>`+DATA.repos.map(r=>`<option>${r}</option>`).join("");
 const draw=()=>{$("#tags").innerHTML=[...DATA.tags].filter(t=>!sel.value||t.r===sel.value).sort((a,b)=>b.d.localeCompare(a.d)).map(t=>`<div class="ev"><div class="d">${day(t.d)} · <span class="sw" style="background:${color(t.r)}"></span> ${t.r}</div><div><span class="mono">${esc(t.t)}</span> ${esc(t.s)}</div></div>`).join("")};sel.onchange=draw;draw()}
function drawLog(){const sel=$("#logRepo");sel.innerHTML=`<option value="">all repos</option>`+DATA.repos.map(r=>`<option>${r}</option>`).join("");
 const draw=()=>{const q=$("#q").value.toLowerCase();const rows=[...C].reverse().filter(c=>(!sel.value||c.r===sel.value)&&(!q||c.s.toLowerCase().includes(q)));
  $("#logCount").textContent=`${rows.length} commits`;
  $("#log").innerHTML=`<table><tr><th>when</th><th>repo</th><th>subject</th><th class="num">+</th><th class="num">−</th></tr>${rows.slice(0,600).map(c=>`<tr><td class="mono">${c.d.slice(0,16).replace("T"," ")}</td><td><span class="sw" style="background:${color(c.r)}"></span> ${c.r}</td><td>${esc(c.s)}</td><td class="num">${c.a}</td><td class="num">${c.x}</td></tr>`).join("")}</table>`};
 sel.onchange=draw;$("#q").oninput=draw;draw()}

drawDaily();drawCal();drawWeek();drawRepos();drawRoad();drawDone();drawTags();drawLog();
addEventListener("resize",()=>{drawDaily();$("#road").innerHTML="";drawRoad()});
</script>
</body>
</html>
"""


def main():
    data = collect()
    html = TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    with open(OUT, "w") as f:
        f.write(html)
    print(f"wrote {OUT}: {len(data['commits'])} commits, {len(data['tags'])} tags, "
          f"{len(data['roadmap'])} roadmap versions, {len(data['done'])} done items")


if __name__ == "__main__":
    main()
