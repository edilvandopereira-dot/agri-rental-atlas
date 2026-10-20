/* Deterministic planning models. No market-price assumptions. */
const RentalModels=(()=>{
 const valid=a=>a.every(v=>typeof v==='number'&&Number.isFinite(v));
 const ceil=v=>Math.ceil(v-1e-10);
 function price(p){const {fixed,variable,logistics,available,billable,margin,quote}=p;
  if(!valid([fixed,variable,logistics,available,billable,margin])||[fixed,variable,logistics].some(v=>v<0)||!Number.isInteger(available)||!Number.isInteger(billable)||available<1||available>31||billable<1||billable>available||margin<0||margin>=100||(quote!==null&&(!valid([quote])||quote<=0)))return null;
  const cost=fixed+logistics+variable*billable, floor=cost/(billable*(1-margin/100));
  return {floor,utilisation:billable/available*100,margin:quote===null?null:(quote*billable-cost)/(quote*billable)*100,breakeven:quote===null||quote<=variable?null:ceil((fixed+logistics)/(quote-variable))};
 }
 function farm(p){const {area,capacity,hours,window,owned,charged,rate,freight}=p;
  if(!valid(Object.values(p))||area<=0||capacity<=0||hours<=0||hours>24||!Number.isInteger(window)||window<1||!Number.isInteger(owned)||owned<0||!Number.isInteger(charged)||charged<window||rate<=0||freight<0)return null;
  const required=ceil(area/(capacity*hours*window)),additional=Math.max(0,required-owned);
  return {required,additional,coverage:Math.min(100,owned*capacity*hours*window/area*100),cost:additional*(rate*charged+freight)};
 }
 function csvRows(s){const rows=[];let row=[],cell='',quoted=false;for(let i=0;i<s.length;i++){const c=s[i];if(c==='"'){if(quoted&&s[i+1]==='"'){cell+='"';i++}else quoted=!quoted}else if(c===','&&!quoted){row.push(cell);cell=''}else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell=''}else cell+=c}if(cell||row.length){row.push(cell.replace(/\r$/,''));rows.push(row)}if(quoted)throw Error('Malformed CSV');return rows}
 function fxFromCsv(csv,now=Date.now()){
  const rows=csvRows(csv),header=rows.shift(),ix=k=>header.indexOf(k),needed=['CURRENCY','CURRENCY_DENOM','TIME_PERIOD','OBS_VALUE','OBS_STATUS'];if(needed.some(k=>ix(k)<0))throw Error('Unexpected ECB schema');const found={};let date=null;
  for(const r of rows){if(!r.join('').trim())continue;const code=r[ix('CURRENCY')];if(!['BRL','USD','CNY'].includes(code))continue;
   const day=r[ix('TIME_PERIOD')],value=Number(r[ix('OBS_VALUE')]);if(found[code]||r[ix('CURRENCY_DENOM')]!=='EUR'||!/^\d{4}-\d{2}-\d{2}$/.test(day)||new Date(day+'T00:00:00Z').toISOString().slice(0,10)!==day||!Number.isFinite(value)||value<=0||r[ix('OBS_STATUS')]!=='A'||(date&&day!==date))throw Error('Invalid or unaligned ECB rates');date=day;found[code]=value;
  }if(Object.keys(found).length!==3||Date.parse(date+'T00:00:00Z')>now+86400000)throw Error('Incomplete or future rates');
  return {source:'ECB',reference_date:date,checked_at:new Date(now).toISOString(),brl_per_unit:{BRL:1,USD:found.BRL/found.USD,CNY:found.BRL/found.CNY},eur_rates:found};
 }
 function usableFx(fx,now=Date.now()){return !!fx&&fx.source==='ECB'&&typeof fx.reference_date==='string'&&Number.isFinite(Date.parse(fx.reference_date))&&now-Date.parse(fx.reference_date+'T00:00:00Z')<=4*86400000&&now>=Date.parse(fx.reference_date+'T00:00:00Z')&&['BRL','USD','CNY'].every(k=>Number.isFinite(fx.brl_per_unit?.[k])&&fx.brl_per_unit[k]>0)&&fx.brl_per_unit.BRL===1}
 return {price,farm,fxFromCsv,usableFx};
})();
if(typeof module!=='undefined')module.exports=RentalModels;
