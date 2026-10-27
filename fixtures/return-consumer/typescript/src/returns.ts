export function source(choose:boolean):string|null{if(choose)return "left";return null;}
function tuple():[number,string]{return [1,"left"];}
function record(){return {name:"left",code:1};}
export function use(){const assigned=source(true);const chained=source(false)?.trim();const[a,b]=tuple();const{name,code}=record();}
