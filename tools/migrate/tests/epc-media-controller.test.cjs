/* State/lifecycle fixture, not a browser or a rendered-layout substitute. */
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function emitter(fields = {}) {
  const listeners = new Map();
  return Object.assign(fields, {
    addEventListener(name, action) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(action);
    },
    emit(name, event = {}) {
      for (const action of listeners.get(name) || []) action(event);
    },
  });
}

function element() {
  const attributes = new Map();
  const classes = new Set();
  return emitter({
    hidden: true, disabled: true, inert: false, style: {},
    setAttribute: (name, value) => attributes.set(name, value),
    getAttribute: name => attributes.get(name) ?? null,
    classList: {
      add: name => classes.add(name),
      toggle(name, value) { if (value) classes.add(name); else classes.delete(name); },
    },
  });
}

function fixture({ reduced = false, observer = true, declinesAutoplay = false } = {}) {
  const video = () => ({
    paused: true, controls: false, plays: 0, decline: declinesAutoplay,
    play() {
      this.plays++;
      if (this.decline) return Promise.reject({ name: 'NotAllowedError' });
      this.paused = false;
      return Promise.resolve();
    },
    pause() { this.paused = true; },
  });
  const videos = [video(), video()];
  const bars = [element(), element(), element()];
  const panes = [element(), element(), element()];
  const slides = videos.map(v => Object.assign(element(), { querySelector: () => v }));
  slides.push(Object.assign(element(), { querySelector: () => null }));
  for (const bar of bars) {
    const fill = { style: {} };
    bar.querySelector = () => fill;
  }
  const gallery = element(), toggle = element(), tabs = element(), counter = element();
  toggle.setAttribute('data-play-label', 'Play slideshow');
  toggle.setAttribute('data-pause-label', 'Pause slideshow');
  const workbench = element();
  const inside = new Set([...bars, ...panes, ...slides, ...videos, gallery, toggle, tabs, counter]);
  workbench.contains = target => inside.has(target);
  workbench.querySelector = name => ({ '.lk-sp-gallery': gallery, '.epc-motion-toggle': toggle, '.epc-media-tabs': tabs })[name];
  workbench.querySelectorAll = name => { assert.equal(name, 'video'); return videos; };
  for (const bar of bars) bar.focus = () => workbench.emit('focusin', { target: bar });
  const root = { querySelectorAll: name => ({ '.lk-sp-bar': bars, '.lk-sp-slide': slides, '.lk-sp-pane': panes })[name] };
  const document = emitter({ hidden: false, getElementById: id => ({ 'sp-counter': counter, 'sp-workbench': workbench })[id] });
  const reduce = emitter({ matches: reduced }), hover = emitter({ matches: true });
  const timers = new Map(), frames = new Map();
  let sequence = 0, observed = null, intersect = null;
  const window = {
    matchMedia: query => query.includes('reduced-motion') ? reduce : hover,
    setTimeout(action, dwell) { assert.equal(dwell, 5000); const id = ++sequence; timers.set(id, action); return id; },
    clearTimeout: id => timers.delete(id),
    requestAnimationFrame(action) { const id = ++sequence; frames.set(id, action); return id; },
    cancelAnimationFrame: id => frames.delete(id),
  };
  const context = { root, document, window };
  if (observer) context.IntersectionObserver = class {
    constructor(action) { intersect = value => action([{ isIntersecting: value }]); }
    observe(target) { observed = target; }
  };
  const source = fs.readFileSync(path.join(__dirname, '..', 'epc-media-controller.js'), 'utf8');
  vm.runInNewContext(source, context);
  return { videos, bars, panes, slides, gallery, toggle, counter, workbench, document, reduce, timers, frames, observed,
    show: value => intersect(value),
    preference(value) { reduce.matches = value; reduce.emit('change'); },
    visibility(hidden) { document.hidden = hidden; document.emit('visibilitychange'); },
    key(index, key) { let prevented = false; bars[index].emit('keydown', { key, preventDefault() { prevented = true; } }); assert.equal(prevented, true); },
  };
}

test('offscreen media is not played; the observer targets the gallery', () => {
  const f = fixture();
  assert.equal(f.observed, f.gallery);
  assert.equal(f.timers.size, 0);
  assert.deepEqual(f.videos.map(v => v.plays), [0, 0]);
  f.show(true);
  assert.equal(f.timers.size, 1);
  assert.equal(f.videos[0].paused, false);
  assert.equal(f.videos[1].paused, true);
  f.show(false);
  assert.equal(f.timers.size, 0);
  assert(f.videos.every(v => v.paused));
});

test('one scheduled dwell advances one choice and stops when the gallery leaves', () => {
  const f = fixture(); f.show(true);
  const [id, advance] = [...f.timers.entries()][0];
  f.timers.delete(id); advance();
  assert.equal(f.counter.textContent, '2 / 3');
  assert.equal(f.timers.size, 1);
  assert.equal(f.videos[0].paused, true);
  assert.equal(f.videos[1].paused, false);
  f.show(false);
  assert.equal(f.timers.size, 0);
  assert.equal(f.frames.size, 0);
});

test('explicit Pause survives pointer, focus, visibility and preference exits', () => {
  const f = fixture(); f.show(true); f.toggle.emit('click');
  f.workbench.emit('pointerenter', { pointerType: 'mouse' });
  f.workbench.emit('focusin');
  f.workbench.emit('pointerleave', { pointerType: 'mouse' });
  f.workbench.emit('focusout', { relatedTarget: null });
  f.show(false); f.show(true); f.visibility(true); f.visibility(false);
  f.preference(true); f.preference(false);
  assert.equal(f.timers.size, 0);
  assert(f.videos.every(v => v.paused));
  assert.equal(f.toggle.getAttribute('aria-label'), 'Play slideshow');
  f.toggle.emit('click');
  assert.equal(f.timers.size, 1);
  assert.equal(f.toggle.getAttribute('aria-label'), 'Pause slideshow');
});

test('pointer and focus suspension do not clear each other; touch is not hover', () => {
  const f = fixture(); f.show(true);
  f.workbench.emit('focusin'); f.workbench.emit('pointerenter', { pointerType: 'mouse' });
  f.workbench.emit('pointerleave', { pointerType: 'mouse' });
  assert.equal(f.timers.size, 0);
  f.workbench.emit('focusout', { relatedTarget: null });
  assert.equal(f.timers.size, 1);
  f.workbench.emit('pointerenter', { pointerType: 'mouse' }); f.workbench.emit('focusin');
  f.workbench.emit('focusout', { relatedTarget: null });
  assert.equal(f.timers.size, 0);
  f.workbench.emit('pointerleave', { pointerType: 'mouse' });
  assert.equal(f.timers.size, 1);
  const timer = [...f.timers.keys()];
  f.workbench.emit('pointerenter', { pointerType: 'touch' });
  assert.deepEqual([...f.timers.keys()], timer);
});

test('explicit Play works under reduced motion and new blockers revoke it', () => {
  const f = fixture({ reduced: true }); f.show(true);
  assert.equal(f.toggle.getAttribute('aria-label'), 'Play slideshow');
  assert.equal(f.timers.size, 0); assert.equal(f.videos[0].plays, 0);
  f.workbench.emit('focusin'); f.workbench.emit('pointerenter', { pointerType: 'mouse' });
  f.toggle.emit('click');
  assert.equal(f.timers.size, 1); assert.equal(f.videos[0].paused, false);
  f.workbench.emit('focusin');
  assert.equal(f.timers.size, 0); assert.equal(f.videos[0].paused, true);
  f.toggle.emit('click'); assert.equal(f.timers.size, 1);
  f.preference(true);
  assert.equal(f.timers.size, 0); assert.equal(f.videos[0].paused, true);
});

test('manual keys bind selection, panel isolation and media isolation together', () => {
  const f = fixture({ reduced: true }); f.show(true);
  f.key(0, 'End');
  assert.equal(f.counter.textContent, '3 / 3');
  assert.deepEqual(f.bars.map(b => b.getAttribute('aria-selected')), ['false', 'false', 'true']);
  assert.deepEqual(f.panes.map(p => p.inert), [true, true, false]);
  assert.deepEqual(f.slides.map(s => s.inert), [true, true, false]);
  f.key(2, 'Home'); f.key(0, 'ArrowRight');
  assert.equal(f.counter.textContent, '2 / 3');
  assert.deepEqual(f.panes.map(p => p.inert), [true, false, true]);
  f.key(1, 'ArrowLeft');
  assert.equal(f.counter.textContent, '1 / 3');
  assert.equal(f.timers.size, 0);
});

test('without IntersectionObserver, native current-video playback remains usable', () => {
  const f = fixture({ observer: false });
  assert.equal(f.toggle.hidden, true);
  assert(f.videos.every(v => v.controls));
  assert.deepEqual(f.videos.map(v => v.plays), [0, 0]);
  f.videos[0].play(); f.workbench.emit('focusin');
  assert.equal(f.videos[0].paused, false);
  f.key(0, 'ArrowRight');
  assert.equal(f.videos[0].paused, true);
  assert.deepEqual(f.slides.map(s => s.inert), [true, false, true]);
  f.videos[1].play(); f.workbench.emit('focusout', { relatedTarget: null });
  assert.equal(f.videos[1].paused, false);
  assert.equal(f.timers.size, 0);
  f.visibility(true);
  assert(f.videos.every(v => v.paused));
});

test('declined autoplay becomes native manual playback and does not undo native Pause', async () => {
  const f = fixture({ declinesAutoplay: true }); f.show(true);
  await Promise.resolve();
  assert.equal(f.videos[0].controls, true);
  f.videos[0].decline = false;
  await f.videos[0].play();
  f.videos[0].pause();
  const plays = f.videos[0].plays;
  f.workbench.emit('pointerleave', { pointerType: 'mouse' });
  f.workbench.emit('focusout', { relatedTarget: null });
  assert.equal(f.videos[0].plays, plays);
  assert.equal(f.videos[0].paused, true);
});
