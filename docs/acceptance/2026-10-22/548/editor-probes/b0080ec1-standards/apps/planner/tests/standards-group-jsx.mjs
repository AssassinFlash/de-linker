import React,{useLayoutEffect,useRef} from 'react';
import {jsx as base,jsxs as bases,Fragment} from 'react/jsx-runtime';
import {Group} from 'three';
export {Fragment};
function GroupHost({ref,position,quaternion,children}) {
 const value=useRef(null);if(!value.current)value.current=new Group();
 useLayoutEffect(()=>{value.current.position.set(...position);if(quaternion)value.current.quaternion.copy(quaternion);});
 useLayoutEffect(()=>{ref.current=value.current;return()=>{ref.current=null;globalThis.__nullGroupRefs=(globalThis.__nullGroupRefs??0)+1;};},[ref]);
 return children??null;
}
export function jsx(type,props,key){return base(type==='group'?GroupHost:type,props,key);}
export function jsxs(type,props,key){return bases(type==='group'?GroupHost:type,props,key);}
