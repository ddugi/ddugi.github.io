"use strict";
// Progressive enhancement: all stories and links are already present in HTML.
const filters=document.querySelector("[data-filters]");
if(filters){
 const buttons=Array.from(filters.querySelectorAll("button"));
 const stories=Array.from(document.querySelectorAll("[data-story]"));
 const search=document.querySelector("#story-search");
 const count=document.querySelector("#result-count");
 const empty=document.querySelector("#empty-state");
 const editionLabel=count.dataset.editionLabel;
 let selected="All";
 function update(){
  const term=search.value.trim().toLocaleLowerCase();
  let visible=0;
  for(const story of stories){
   const category=selected==="All"||(selected==="Structural Shifts"?story.dataset.signal==="Structural Shift":story.dataset.category===selected);
   const match=category&&story.dataset.search.includes(term);
   story.hidden=!match;if(match)visible++;
  }
  buttons.forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.filter===selected)));
  count.textContent=visible+" "+(visible===1?"signal":"signals")+" · "+editionLabel;
  empty.hidden=visible!==0;
 }
 filters.addEventListener("click",event=>{const button=event.target.closest("button[data-filter]");if(!button)return;selected=button.dataset.filter;update();});
 search.addEventListener("input",update);
 const reset=document.querySelector("#reset-filters");
 reset.addEventListener("click",()=>{selected="All";search.value="";update();search.focus();});
 const initial=new URLSearchParams(location.search).get("category");
 if(buttons.some(button=>button.dataset.filter===initial))selected=initial;
 filters.hidden=false;document.querySelector("[data-search]").hidden=false;update();
}

