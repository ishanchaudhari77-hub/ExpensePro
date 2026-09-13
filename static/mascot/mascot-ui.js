(() => {
    "use strict";

    if (window.RupyMascotUI) return;

    const DEFAULT_STORAGE_KEY = "expensepro-rupy-position-v1";
    const DRAG_DISTANCE_THRESHOLD = 4;

    const parsePosition = (rawValue) => {
        try {
            const parsed = JSON.parse(String(rawValue || "{}"));
            const x = Number(parsed?.x);
            const y = Number(parsed?.y);
            if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
            return { x, y };
        } catch (_) {
            return null;
        }
    };

    class RupyUI {
        constructor(rootNode, options = {}) {
            this.rootNode = rootNode;
            this.avatarNode = rootNode.querySelector("[data-rupy-float-toggle]");
            this.imageNode = rootNode.querySelector("[data-rupy-float-image]");
            this.bubbleNode = rootNode.querySelector("[data-rupy-float-bubble]");
            this.storageKey = String(options.storageKey || DEFAULT_STORAGE_KEY);
            this.stateNames = Array.isArray(options.stateNames) ? options.stateNames : [];
            this.messageTimer = null;
            this.animationTimer = null;
            this.dragData = null;
            this.wasDragged = false;
            this.hoverHandlers = [];
            this.positionPinned = false;
        }

        init() {
            if (!this.rootNode || !this.avatarNode || !this.imageNode) return;
            this.rootNode.classList.add("rupy-modern", "is-draggable");
            this.restorePosition();
            this.bindToggle();
            this.bindDrag();
            this.bindHover();
            this.bindResizeClamp();
        }

        bindToggle() {
            this.avatarNode.addEventListener("click", (event) => {
                if (this.wasDragged) {
                    this.wasDragged = false;
                    event.preventDefault();
                    event.stopPropagation();
                    return;
                }
                this.rootNode.classList.toggle("is-collapsed");
            });
        }

        bindHover() {
            this.avatarNode.addEventListener("pointerenter", () => {
                this.hoverHandlers.forEach((handler) => {
                    try {
                        handler();
                    } catch (_) {
                        // Ignore listener errors so mascot UI keeps working.
                    }
                });
            });
        }

        bindResizeClamp() {
            window.addEventListener("resize", () => {
                if (!this.positionPinned) return;
                const current = this.readCurrentPosition();
                this.applyPosition(this.clampPosition(current.x, current.y), false);
            });
        }

        bindDrag() {
            const onPointerMove = (event) => {
                if (!this.dragData) return;
                const deltaX = event.clientX - this.dragData.startPointerX;
                const deltaY = event.clientY - this.dragData.startPointerY;

                if (!this.dragData.dragging) {
                    const movedEnough = Math.hypot(deltaX, deltaY) >= DRAG_DISTANCE_THRESHOLD;
                    if (!movedEnough) return;
                    this.dragData.dragging = true;
                    this.wasDragged = true;
                    this.rootNode.classList.add("is-dragging");
                }

                const nextX = this.dragData.startX + deltaX;
                const nextY = this.dragData.startY + deltaY;
                this.applyPosition(this.clampPosition(nextX, nextY), false);
            };

            const endDrag = (event) => {
                if (!this.dragData) return;
                if (this.dragData.dragging) {
                    this.applyPosition(this.clampPosition(
                        this.dragData.startX + (event.clientX - this.dragData.startPointerX),
                        this.dragData.startY + (event.clientY - this.dragData.startPointerY)
                    ), true);
                }
                this.rootNode.classList.remove("is-dragging");
                this.dragData = null;
            };

            this.avatarNode.addEventListener("pointerdown", (event) => {
                if (event.button !== 0) return;

                this.pinToCurrentPosition();
                const currentPosition = this.readCurrentPosition();
                this.dragData = {
                    pointerId: event.pointerId,
                    startPointerX: event.clientX,
                    startPointerY: event.clientY,
                    startX: currentPosition.x,
                    startY: currentPosition.y,
                    dragging: false,
                };

                this.avatarNode.setPointerCapture(event.pointerId);
                event.preventDefault();
            });

            this.avatarNode.addEventListener("pointermove", onPointerMove);
            this.avatarNode.addEventListener("pointerup", endDrag);
            this.avatarNode.addEventListener("pointercancel", endDrag);
        }

        pinToCurrentPosition() {
            if (this.positionPinned) return;
            const rect = this.rootNode.getBoundingClientRect();
            const position = this.clampPosition(rect.left, rect.top);
            this.rootNode.style.left = `${position.x}px`;
            this.rootNode.style.top = `${position.y}px`;
            this.rootNode.style.right = "auto";
            this.rootNode.style.bottom = "auto";
            this.positionPinned = true;
        }

        readCurrentPosition() {
            const rect = this.rootNode.getBoundingClientRect();
            return { x: rect.left, y: rect.top };
        }

        clampPosition(x, y) {
            const rect = this.rootNode.getBoundingClientRect();
            const maxX = Math.max(0, window.innerWidth - rect.width);
            const maxY = Math.max(0, window.innerHeight - rect.height);
            return {
                x: Math.min(maxX, Math.max(0, Number(x) || 0)),
                y: Math.min(maxY, Math.max(0, Number(y) || 0)),
            };
        }

        applyPosition(position, persist) {
            this.pinToCurrentPosition();
            this.rootNode.style.left = `${position.x}px`;
            this.rootNode.style.top = `${position.y}px`;
            this.rootNode.style.right = "auto";
            this.rootNode.style.bottom = "auto";
            if (persist) {
                try {
                    localStorage.setItem(this.storageKey, JSON.stringify(position));
                } catch (_) {
                    // Ignore storage write issues.
                }
            }
        }

        restorePosition() {
            let storedPosition = null;
            try {
                storedPosition = parsePosition(localStorage.getItem(this.storageKey));
            } catch (_) {
                storedPosition = null;
            }
            if (!storedPosition) return;
            const clamped = this.clampPosition(storedPosition.x, storedPosition.y);
            this.applyPosition(clamped, false);
        }

        resetPosition() {
            try {
                localStorage.removeItem(this.storageKey);
            } catch (_) {
                // Ignore storage remove issues.
            }
            this.positionPinned = false;
            this.rootNode.style.left = "";
            this.rootNode.style.top = "";
            this.rootNode.style.right = "";
            this.rootNode.style.bottom = "";
            this.rootNode.classList.remove("is-dragging");
        }

        setState(stateName, options = {}) {
            const normalized = String(stateName || "idle").trim().toLowerCase();
            this.stateNames.forEach((name) => {
                this.rootNode.classList.remove(`state-${name}`);
            });
            this.rootNode.classList.add(`state-${normalized}`);

            const animation = String(options.animation || "").trim();
            this.rootNode.classList.remove(
                "anim-bounce",
                "anim-pop",
                "anim-shake",
                "anim-jump",
                "anim-wiggle"
            );
            if (animation) {
                this.rootNode.classList.add(`anim-${animation}`);
                if (this.animationTimer) window.clearTimeout(this.animationTimer);
                this.animationTimer = window.setTimeout(() => {
                    this.rootNode.classList.remove(`anim-${animation}`);
                }, 980);
            }
        }

        setImage(src) {
            const nextSrc = String(src || "").trim();
            if (!nextSrc) return;
            if (String(this.imageNode.getAttribute("src") || "").trim() === nextSrc) return;

            this.rootNode.classList.add("is-image-transition");
            this.imageNode.setAttribute("loading", "lazy");
            this.imageNode.setAttribute("decoding", "async");

            const loader = new Image();
            loader.decoding = "async";
            loader.loading = "lazy";
            loader.src = nextSrc;

            const finalize = () => {
                this.imageNode.setAttribute("src", nextSrc);
                window.requestAnimationFrame(() => {
                    this.rootNode.classList.remove("is-image-transition");
                });
            };

            if (typeof loader.decode === "function") {
                loader.decode().then(finalize).catch(finalize);
            } else {
                loader.onload = finalize;
                loader.onerror = finalize;
            }
        }

        speak(message, durationMs = 4200) {
            if (!this.bubbleNode) return;
            const text = String(message || "").trim();
            if (!text) return;

            if (this.messageTimer) window.clearTimeout(this.messageTimer);
            this.bubbleNode.textContent = text;
            this.rootNode.classList.remove("is-collapsed");

            const holdMs = Math.max(1200, Number(durationMs) || 0);
            this.messageTimer = window.setTimeout(() => {
                this.rootNode.classList.add("is-collapsed");
            }, holdMs);
        }

        onHover(handler) {
            if (typeof handler !== "function") return;
            this.hoverHandlers.push(handler);
        }
    }

    window.RupyMascotUI = Object.freeze({
        create(rootNode, options = {}) {
            if (!rootNode) return null;
            const ui = new RupyUI(rootNode, options);
            ui.init();
            return ui;
        },
    });
})();
