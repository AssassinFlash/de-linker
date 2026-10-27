import React, {useEffect, useState} from 'react';
import {context, useThree} from '@react-three/fiber';
import {createStore} from 'zustand/vanilla';
import {PerspectiveCamera, Scene} from 'three/webgpu';
export {useThree};

// Control only Canvas/GPU ownership. SceneViewport, SceneCamera, OrbitController,
// RendererLifecycle, real R3F useThree/context and Three camera mathematics run.
// Meshes/GPU drawing are excluded; this is explicitly not native renderer proof.
export function Canvas(props) {
  const host = globalThis.__cameraHost;
  const [store] = useState(() => {
    const camera = new PerspectiveCamera(props.camera.fov, host.width/host.height, .1, 2000);
    camera.position.set(...props.camera.position);
    const canvas = document.createElement('canvas');
    return createStore(() => ({camera, size: {width:host.width,height:host.height}, scene:new Scene(), gl:{domElement:canvas}, invalidate() {host.invalidations++;}}));
  });
  host.props=props;host.store=store;
  useEffect(() => {host.mounts++; return () => {host.unmounts++;};}, []);
  const children=React.Children.toArray(props.children).filter(node => ['SceneCamera','OrbitController','RendererLifecycle'].includes(node.type?.name));
  return React.createElement(context.Provider,{value:store},children);
}
