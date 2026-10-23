      // 2. EPC media lifecycle: native choices, visible media and deliberate motion.
      var spBars = Array.from(root.querySelectorAll('.lk-sp-bar'));
      var spSlides = Array.from(root.querySelectorAll('.lk-sp-slide'));
      var spPanes = Array.from(root.querySelectorAll('.lk-sp-pane'));
      var spCounter = document.getElementById('sp-counter');
      var workbench = document.getElementById('sp-workbench');
      var mediaGallery = workbench.querySelector('.lk-sp-gallery');
      var motionButton = workbench.querySelector('.epc-motion-toggle');
      var mediaTabs = workbench.querySelector('.epc-media-tabs');
      var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
      var hoverPointer = window.matchMedia('(hover: hover)');
      var currentIndex = 0;
      var totalSlides = spBars.length;
      var autoTimer = null;
      var progressFrame = null;
      // Retain the existing page's five-second dwell; do not create a new interval.
      var slideDuration = 5000;
      var galleryVisible = false;
      var canObserveMedia = typeof IntersectionObserver === 'function';
      var userPaused = false;
      var explicitPlay = false;
      var pointerInside = false;
      var focusWithin = false;
      var manualVideos = new WeakSet();

      function rotationAllowed() {
        return galleryVisible && !document.hidden && !userPaused &&
          (explicitPlay || (!reducedMotion.matches && !pointerInside && !focusWithin));
      }

      function videoAllowed() {
        return galleryVisible && !document.hidden && !userPaused &&
          (explicitPlay || !reducedMotion.matches);
      }

      function stopTimer() {
        if (autoTimer !== null) window.clearTimeout(autoTimer);
        if (progressFrame !== null) window.cancelAnimationFrame(progressFrame);
        autoTimer = progressFrame = null;
      }

      function updateMedia() {
        spSlides.forEach(function(slide, index) {
          var video = slide.querySelector('video');
          if (!video) return;
          if (!canObserveMedia || manualVideos.has(video)) {
            // Keep the selected native controls usable; never start them here.
            if (index !== currentIndex || document.hidden || userPaused) video.pause();
            return;
          }
          if (index !== currentIndex || !videoAllowed()) {
            video.pause();
            return;
          }
          if (video.paused) {
            var playing = video.play();
            if (playing) playing.catch(function(error) {
              // Native controls keep playback available if autoplay is declined.
              if (error.name !== 'AbortError' && index === currentIndex && videoAllowed()) {
                manualVideos.add(video);
                video.controls = true;
              }
            });
          }
        });
      }

      function synchronize() {
        stopTimer();
        var paused = userPaused || (reducedMotion.matches && !explicitPlay);
        motionButton.setAttribute('aria-label', motionButton.getAttribute(paused ? 'data-play-label' : 'data-pause-label'));
        motionButton.classList.toggle('is-paused', paused);
        updateMedia();
        spBars.forEach(function(bar, index) {
          var fill = bar.querySelector('.lk-sp-bar-fill');
          fill.style.transition = 'none';
          fill.style.width = index < currentIndex ? '100%' : '0%';
        });
        if (!rotationAllowed()) return;
        var selected = currentIndex;
        progressFrame = window.requestAnimationFrame(function() {
          progressFrame = null;
          if (!rotationAllowed() || selected !== currentIndex) return;
          var fill = spBars[selected].querySelector('.lk-sp-bar-fill');
          fill.style.transition = 'width ' + (slideDuration / 1000) + 's linear';
          fill.style.width = '100%';
        });
        autoTimer = window.setTimeout(function() {
          autoTimer = null;
          activateSlide((currentIndex + 1) % totalSlides);
        }, slideDuration);
      }

      function activateSlide(index) {
        currentIndex = index;
        spBars.forEach(function(bar, i) {
          var active = i === index;
          bar.classList.toggle('active', active);
          bar.setAttribute('aria-selected', String(active));
          bar.tabIndex = active ? 0 : -1;
        });
        spSlides.forEach(function(slide, i) {
          slide.classList.toggle('active', i === index);
          slide.setAttribute('aria-hidden', String(i !== index));
          slide.inert = i !== index;
        });
        spPanes.forEach(function(pane, i) {
          pane.classList.toggle('active', i === index);
          pane.setAttribute('aria-hidden', String(i !== index));
          pane.inert = i !== index;
        });
        spCounter.textContent = (index + 1) + ' / ' + totalSlides;
        synchronize();
      }

      spBars.forEach(function(bar, index) {
        bar.disabled = false;
        bar.addEventListener('click', function() { activateSlide(index); });
        bar.addEventListener('keydown', function(event) {
          var next = index;
          if (event.key === 'ArrowRight') next = (index + 1) % totalSlides;
          else if (event.key === 'ArrowLeft') next = (index - 1 + totalSlides) % totalSlides;
          else if (event.key === 'Home') next = 0;
          else if (event.key === 'End') next = totalSlides - 1;
          else return;
          event.preventDefault();
          activateSlide(next);
          spBars[next].focus();
        });
      });
      motionButton.addEventListener('click', function() {
        var wantsPlay = userPaused || (reducedMotion.matches && !explicitPlay);
        userPaused = !wantsPlay;
        explicitPlay = wantsPlay;
        synchronize();
      });
      workbench.addEventListener('pointerenter', function(event) {
        if (event.pointerType === 'touch' || !hoverPointer.matches) return;
        pointerInside = true;
        explicitPlay = false;
        synchronize();
      });
      workbench.addEventListener('pointerleave', function(event) {
        if (event.pointerType === 'touch') return;
        pointerInside = false;
        synchronize();
      });
      workbench.addEventListener('focusin', function() {
        focusWithin = true;
        explicitPlay = false;
        synchronize();
      });
      workbench.addEventListener('focusout', function(event) {
        focusWithin = workbench.contains(event.relatedTarget);
        synchronize();
      });
      document.addEventListener('visibilitychange', function() {
        if (document.hidden) explicitPlay = false;
        synchronize();
      });
      reducedMotion.addEventListener('change', function() {
        explicitPlay = false;
        synchronize();
      });
      hoverPointer.addEventListener('change', function() {
        pointerInside = false;
        explicitPlay = false;
        synchronize();
      });
      workbench.classList.add('epc-media-ready');
      mediaTabs.hidden = spCounter.hidden = false;
      motionButton.hidden = !canObserveMedia;
      activateSlide(0);
      if (canObserveMedia) {
        var mediaObserver = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (galleryVisible === entry.isIntersecting) return;
            galleryVisible = entry.isIntersecting;
            if (!galleryVisible) explicitPlay = false;
            synchronize();
          });
        });
        mediaObserver.observe(mediaGallery);
      } else {
        // No offscreen eager-play fallback: retain native on-demand playback.
        workbench.querySelectorAll('video').forEach(function(video) { video.controls = true; });
      }
