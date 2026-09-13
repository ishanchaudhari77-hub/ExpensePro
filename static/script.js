// ===============================
// ExpensePro UI Scripts
// ===============================

function parseJsonScript(id, fallbackValue) {
    const element = document.getElementById(id);
    if (!element) return fallbackValue;
    try {
        const parsed = JSON.parse(element.textContent || "null");
        return parsed === null ? fallbackValue : parsed;
    } catch (_) {
        return fallbackValue;
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

const LOGIN_TRANSITION_STORAGE_KEY = "expensepro-login-transition";
const SPLASH_SEEN_STORAGE_KEY = "expensepro-splash-seen-v1";
const SPLASH_FORCE_STORAGE_KEY = "expensepro-splash-force-v1";
const TOAST_DEFAULT_DURATION = {
    success: 2600,
    info: 3200,
    warning: 3200,
    error: 4500,
};

const UI_COPY = {
    en: {
        appearance_updated: "Appearance preferences updated.",
        appearance_save_failed: "Could not save appearance. Please retry.",
    },
    hi: {
        appearance_updated: "दिखावट सेटिंग्स अपडेट हो गईं।",
        appearance_save_failed: "दिखावट सेव नहीं हो सकी। फिर से कोशिश करें।",
    },
};

let toastContainer = null;
let splashRevealDelayMs = 0;
let lottieLoaderPromise = null;
let deleteSuccessAnim = null;
let deleteSuccessTimer = null;

function uiLanguage() {
    const lang = String(document.body?.dataset?.language || "en").trim().toLowerCase();
    return lang === "hi" ? "hi" : "en";
}

function uiCopy(key, fallback = "") {
    const lang = uiLanguage();
    const langMap = UI_COPY[lang] || UI_COPY.en || {};
    const defaultMap = UI_COPY.en || {};
    return langMap[key] || defaultMap[key] || fallback || key;
}

function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function clampNumber(value, min, max) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return min;
    return Math.min(max, Math.max(min, numericValue));
}

const RUPY_CORE_STATES = [
    "idle",
    "thinking",
    "warning",
    "success",
    "error",
    "celebrate",
    "sleep",
    "focus",
    "peek",
    "wave",
    "lazy",
    "money-rain",
    "login",
];
const RUPY_STATE_TRANSITION_COOLDOWN_MS = 180;
const RUPY_CELEBRATION_TIERS = ["small", "medium", "epic"];
const RUPY_BUDGET_STRESS_LEVELS = ["low", "medium", "high", "critical"];

function createRupyStateMachine(node, options = {}) {
    if (!node) {
        return {
            getState() { return "idle"; },
            transition() {},
            cancelPending() {},
        };
    }

    const classPrefix = String(options.classPrefix || "state-");
    const initialState = String(options.initialState || "idle").trim().toLowerCase();
    let currentState = RUPY_CORE_STATES.includes(initialState) ? initialState : "idle";
    const onTransition = (typeof options.onTransition === "function") ? options.onTransition : null;
    const transitionCooldownMs = Math.max(
        0,
        Number(options.cooldownMs ?? RUPY_STATE_TRANSITION_COOLDOWN_MS) || RUPY_STATE_TRANSITION_COOLDOWN_MS
    );
    let queuedTransition = null;
    let queuedTimer = null;
    let lastTransitionAt = 0;

    const applyStateClass = (stateName) => {
        RUPY_CORE_STATES.forEach((state) => {
            node.classList.remove(`${classPrefix}${state}`);
        });
        node.classList.add(`${classPrefix}${stateName}`);
    };

    const clearQueuedTransition = () => {
        queuedTransition = null;
        if (!queuedTimer) return;
        window.clearTimeout(queuedTimer);
        queuedTimer = null;
    };

    const applyTransition = (stateName, meta = {}) => {
        const previousState = currentState;
        currentState = stateName;
        applyStateClass(stateName);
        lastTransitionAt = Date.now();
        if (onTransition) onTransition(previousState, stateName, meta);
    };

    const scheduleQueuedTransition = (stateName, meta, waitMs) => {
        queuedTransition = { stateName, meta };
        if (queuedTimer) return;
        queuedTimer = window.setTimeout(() => {
            queuedTimer = null;
            if (!queuedTransition) return;
            const queued = queuedTransition;
            queuedTransition = null;
            applyTransition(queued.stateName, {
                ...queued.meta,
                queued: true,
                force: true,
            });
        }, Math.max(20, waitMs));
    };

    applyStateClass(currentState);
    lastTransitionAt = Date.now();

    return {
        getState() {
            return currentState;
        },
        transition(nextState, meta = {}) {
            const normalizedState = String(nextState || "").trim().toLowerCase();
            const safeState = RUPY_CORE_STATES.includes(normalizedState) ? normalizedState : "idle";
            const isForced = Boolean(meta.force || meta.immediate || meta.sequenceStep);
            const now = Date.now();
            const elapsed = now - lastTransitionAt;

            if (!isForced) {
                if (safeState === currentState && elapsed < transitionCooldownMs) {
                    return false;
                }
                if (elapsed < transitionCooldownMs) {
                    scheduleQueuedTransition(safeState, meta, transitionCooldownMs - elapsed + 12);
                    return false;
                }
            }

            clearQueuedTransition();
            applyTransition(safeState, meta);
            return true;
        },
        cancelPending() {
            clearQueuedTransition();
        },
    };
}

function runRupyStateSequence(setStateFn, steps = []) {
    if (typeof setStateFn !== "function" || !Array.isArray(steps) || !steps.length) {
        return () => {};
    }

    const timers = [];
    let elapsedMs = 0;

    steps.forEach((step, index) => {
        const stateName = String(step?.state || "").replace(/^state-/, "").trim().toLowerCase() || "idle";
        if (index > 0) {
            const previousDelay = Math.max(0, Number(steps[index - 1]?.delayMs) || 0);
            elapsedMs += previousDelay;
        }

        const timer = window.setTimeout(() => {
            setStateFn(stateName, {
                ...(step?.options || {}),
                force: true,
                sequenceStep: true,
            });
        }, elapsedMs);
        timers.push(timer);
    });

    return () => {
        timers.forEach((timerId) => window.clearTimeout(timerId));
    };
}

function normalizeRupyCelebrationTier(rawTier) {
    const normalized = String(rawTier || "").trim().toLowerCase();
    if (RUPY_CELEBRATION_TIERS.includes(normalized)) return normalized;
    return "small";
}

function applyRupyCelebrationTier(node, tierName) {
    if (!node) return;
    node.dataset.rupyTier = normalizeRupyCelebrationTier(tierName);
}

function inferRupyCelebrationTier({ spentPercent = 0, budgetLeft = 0, totalBudget = 0, forecastOver = 0 } = {}) {
    const spent = Number(spentPercent) || 0;
    const remaining = Number(budgetLeft) || 0;
    const budget = Number(totalBudget) || 0;
    const over = Number(forecastOver) || 0;
    const bufferRatio = budget > 0 ? remaining / budget : 0;

    if (over > 0 || remaining <= 0) return "small";
    if (spent <= 55 && bufferRatio >= 0.3) return "epic";
    if (spent <= 75 && bufferRatio >= 0.12) return "medium";
    return "small";
}

function inferRupyBudgetStressLevel({ spentPercent = 0, budgetLeft = 0, forecastOver = 0, budgetRemaining = null } = {}) {
    const spent = Number(spentPercent);
    const remaining = Number.isFinite(Number(budgetRemaining))
        ? (Number(budgetRemaining) || 0)
        : (Number(budgetLeft) || 0);
    const over = Number(forecastOver) || 0;

    if (over > 0 || remaining < 0 || spent >= 100) return "critical";
    if (spent >= 85 || remaining === 0) return "high";
    if (spent >= 70 || remaining <= 2000) return "medium";
    return "low";
}

function applyRupyBudgetStressLevel(node, rawLevel) {
    if (!node) return;
    const normalized = String(rawLevel || "").trim().toLowerCase();
    node.dataset.rupyStress = RUPY_BUDGET_STRESS_LEVELS.includes(normalized) ? normalized : "low";
}

function normalizeToastType(type) {
    const cleanType = String(type || "").trim().toLowerCase();
    if (["success", "info", "warning", "error"].includes(cleanType)) return cleanType;
    return "info";
}

function toastIcon(type) {
    const iconMap = {
        success: "fa-solid fa-circle-check",
        info: "fa-solid fa-circle-info",
        warning: "fa-solid fa-triangle-exclamation",
        error: "fa-solid fa-triangle-exclamation",
    };
    return iconMap[type] || iconMap.info;
}

function dismissToast(toastNode) {
    if (!toastNode || toastNode.dataset.closing === "true") return;
    toastNode.dataset.closing = "true";

    if (prefersReducedMotion()) {
        toastNode.remove();
        return;
    }

    toastNode.classList.remove("show");
    toastNode.classList.add("hide");
    window.setTimeout(() => {
        toastNode.remove();
    }, 180);
}

function showAppToast(message, type = "info", durationMs = null) {
    if (!toastContainer) return;

    const finalType = normalizeToastType(type);
    const duration = Number(durationMs || TOAST_DEFAULT_DURATION[finalType] || TOAST_DEFAULT_DURATION.info);
    const text = String(message || "").trim();
    if (!text) return;

    const toastNode = document.createElement("article");
    toastNode.className = `toast toast-${finalType}`;
    toastNode.setAttribute("role", "status");
    toastNode.innerHTML = `
        <span class="toast-icon"><i class="${toastIcon(finalType)}"></i></span>
        <p class="toast-copy">${escapeHtml(text)}</p>
        <button type="button" class="toast-close" aria-label="Dismiss message">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;

    const closeButton = toastNode.querySelector(".toast-close");
    let dismissTimer = null;
    let startedAt = Date.now();
    let remaining = duration;

    const clearTimer = () => {
        if (dismissTimer) {
            window.clearTimeout(dismissTimer);
            dismissTimer = null;
        }
    };

    const scheduleDismiss = () => {
        clearTimer();
        startedAt = Date.now();
        dismissTimer = window.setTimeout(() => {
            dismissToast(toastNode);
        }, remaining);
    };

    toastNode.addEventListener("mouseenter", () => {
        if (prefersReducedMotion()) return;
        const elapsed = Date.now() - startedAt;
        remaining = Math.max(500, remaining - elapsed);
        clearTimer();
    });

    toastNode.addEventListener("mouseleave", () => {
        if (prefersReducedMotion()) return;
        scheduleDismiss();
    });

    if (closeButton) {
        closeButton.addEventListener("click", () => {
            clearTimer();
            dismissToast(toastNode);
        });
    }

    while (toastContainer.children.length >= 3) {
        const firstToast = toastContainer.firstElementChild;
        if (!firstToast) break;
        dismissToast(firstToast);
        if (prefersReducedMotion()) break;
    }

    toastContainer.appendChild(toastNode);
    if (!prefersReducedMotion()) {
        window.requestAnimationFrame(() => {
            toastNode.classList.add("show");
        });
    } else {
        toastNode.classList.add("show");
    }
    scheduleDismiss();
}

function ensureLottieLoaded() {
    if (window.lottie && typeof window.lottie.loadAnimation === "function") {
        return Promise.resolve(window.lottie);
    }

    if (lottieLoaderPromise) {
        return lottieLoaderPromise;
    }

    lottieLoaderPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js";
        script.async = true;
        script.onload = () => {
            if (window.lottie && typeof window.lottie.loadAnimation === "function") {
                resolve(window.lottie);
                return;
            }
            reject(new Error("Lottie loaded without API"));
        };
        script.onerror = () => reject(new Error("Failed to load Lottie library"));
        document.head.appendChild(script);
    });

    return lottieLoaderPromise;
}

function categoryDeleteCelebrationLabel(message) {
    const text = String(message || "").trim();
    if (!text) return "Category removed successfully";

    const matchedName = text.match(/category deleted:\s*([^.,]+)/i);
    if (!matchedName || !matchedName[1]) return "Category removed successfully";

    const categoryName = matchedName[1].trim();
    return categoryName ? `${categoryName} removed successfully` : "Category removed successfully";
}

function formatRupyMonth(monthKey) {
    const raw = String(monthKey || "").trim();
    const matched = raw.match(/^(\d{4})-(\d{2})$/);
    if (!matched) return raw || "selected month";
    const year = Number(matched[1]);
    const month = Number(matched[2]);
    if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return raw;
    const date = new Date(Date.UTC(year, month - 1, 1));
    return date.toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
        timeZone: "UTC",
    });
}

function mapRupyNotification(message, category) {
    const rawMessage = String(message || "").trim();
    const rawType = normalizeToastType(category);
    if (!rawMessage) {
        return {
            message: rawMessage,
            type: rawType,
        };
    }

    const expenseAdded = rawMessage.match(/^Expense added:\s*([^|]+)\|\s*(.+)$/i);
    if (expenseAdded) {
        return {
            message: `Rupy: Logged ${expenseAdded[1].trim()} in ${expenseAdded[2].trim()}.`,
            type: "success",
        };
    }

    const expenseUpdated = rawMessage.match(/^Expense updated:\s*([^|]+)\|\s*(.+)$/i);
    if (expenseUpdated) {
        return {
            message: `Rupy: Updated to ${expenseUpdated[1].trim()} in ${expenseUpdated[2].trim()}.`,
            type: "success",
        };
    }

    const incomeAdded = rawMessage.match(/^Income added:\s*([^|]+)\|\s*(.+)$/i);
    if (incomeAdded) {
        return {
            message: `Rupy: Added income ${incomeAdded[1].trim()} from ${incomeAdded[2].trim()}.`,
            type: "success",
        };
    }

    const incomeUpdated = rawMessage.match(/^Income updated:\s*([^|]+)\|\s*(.+)$/i);
    if (incomeUpdated) {
        return {
            message: `Rupy: Updated income to ${incomeUpdated[1].trim()} from ${incomeUpdated[2].trim()}.`,
            type: "success",
        };
    }

    const deletedExpense = rawMessage.match(/^Deleted:\s*(.+?)\s+expense\.?$/i);
    if (deletedExpense) {
        return {
            message: `Rupy: Removed ${deletedExpense[1].trim()} expense entry.`,
            type: "warning",
        };
    }

    const deletedIncome = rawMessage.match(/^Deleted:\s*(.+?)\s+income entry\.?$/i);
    if (deletedIncome) {
        return {
            message: `Rupy: Removed ${deletedIncome[1].trim()} income entry.`,
            type: "warning",
        };
    }

    const categoryAdded = rawMessage.match(/^Category added:\s*(.+)$/i);
    if (categoryAdded) {
        return {
            message: `Rupy: Category ${categoryAdded[1].trim()} is ready to use.`,
            type: "success",
        };
    }

    const categoryExists = rawMessage.match(/^Category already exists:\s*(.+)$/i);
    if (categoryExists) {
        return {
            message: `Rupy: ${categoryExists[1].trim()} already exists. Pick it from the list.`,
            type: "info",
        };
    }

    const categoryDeleted = rawMessage.match(/^Category deleted:\s*(.+?)\.\s*Moved existing expenses to Other\./i);
    if (categoryDeleted) {
        return {
            message: `Rupy: Deleted ${categoryDeleted[1].trim()}. Existing records moved to Other.`,
            type: "warning",
        };
    }

    const budgetSaved = rawMessage.match(/^Budget saved for\s+([0-9]{4}-[0-9]{2})\./i);
    if (budgetSaved) {
        return {
            message: `Rupy: Budget plan updated for ${formatRupyMonth(budgetSaved[1])}.`,
            type: "success",
        };
    }

    const monthlyExceeded = rawMessage.match(/^Monthly budget exceeded by\s+(.+?)\.?$/i);
    if (monthlyExceeded) {
        return {
            message: `Rupy Alert: Budget exceeded by ${monthlyExceeded[1].trim()}.`,
            type: "warning",
        };
    }

    const monthlyUsage = rawMessage.match(/^Monthly budget usage is\s+(\d+)%\.?$/i);
    if (monthlyUsage) {
        return {
            message: `Rupy Alert: Monthly usage reached ${monthlyUsage[1]}%.`,
            type: "warning",
        };
    }

    const categoryCrossed = rawMessage.match(/^(.+?) crossed its category budget\.?$/i);
    if (categoryCrossed) {
        return {
            message: `Rupy Alert: ${categoryCrossed[1].trim()} is over its category limit.`,
            type: "warning",
        };
    }

    const categoryNear = rawMessage.match(/^(.+?) is near category budget\.?$/i);
    if (categoryNear) {
        return {
            message: `Rupy Alert: ${categoryNear[1].trim()} is near its category limit.`,
            type: "warning",
        };
    }

    const goalCreated = rawMessage.match(/^Goal created:\s*(.+)$/i);
    if (goalCreated) {
        return {
            message: `Rupy: New goal locked in - ${goalCreated[1].trim()}.`,
            type: "success",
        };
    }

    if (/^Goal marked as completed\.?$/i.test(rawMessage)) {
        return {
            message: "Rupy Celebration: Goal completed. Momentum is strong.",
            type: "success",
        };
    }

    if (/^Goal archived\.?$/i.test(rawMessage)) {
        return {
            message: "Rupy: Goal archived. You can reactivate anytime.",
            type: "info",
        };
    }

    if (/^Goal moved back to active\.?$/i.test(rawMessage)) {
        return {
            message: "Rupy: Goal is active again. Let's finish it.",
            type: "info",
        };
    }

    const goalDeleted = rawMessage.match(/^Goal deleted:\s*(.+)$/i);
    if (goalDeleted) {
        return {
            message: `Rupy: Goal removed - ${goalDeleted[1].trim()}.`,
            type: "warning",
        };
    }

    const levelUnlocked = rawMessage.match(/^Gamification:\s*\+(.+?)\s*XP\.\s*Level\s+(\d+)\s+unlocked\.?$/i);
    if (levelUnlocked) {
        return {
            message: `Rupy Celebration: Level ${levelUnlocked[2]} unlocked. Money skills upgraded.`,
            type: "success",
        };
    }

    const xpEarned = rawMessage.match(/^Gamification:\s*\+(.+?)\s*XP earned\.?$/i);
    if (xpEarned) {
        return {
            message: `Rupy: Nice progress. +${xpEarned[1].trim()} XP added.`,
            type: "success",
        };
    }

    if (/no spend day/i.test(rawMessage)) {
        return {
            message: "Rupy Celebration: No Spend Day complete. Coins unlocked.",
            type: "success",
        };
    }

    if (/streak/i.test(rawMessage) && /(day|days)/i.test(rawMessage)) {
        return {
            message: `Rupy: ${rawMessage}`,
            type: "info",
        };
    }

    if (/^profile updated successfully\.?$/i.test(rawMessage)) {
        return {
            message: "Rupy: Profile details updated successfully.",
            type: "success",
        };
    }

    if (/^profile photo updated\.?$/i.test(rawMessage)) {
        return {
            message: "Rupy: Profile photo updated successfully.",
            type: "success",
        };
    }

    if (/^password updated successfully\.?$/i.test(rawMessage)) {
        return {
            message: "Rupy: Password updated. Account security is stronger now.",
            type: "success",
        };
    }

    if (/^welcome back,\s*/i.test(rawMessage)) {
        return {
            message: "Rupy: Welcome back. Your dashboard is ready.",
            type: "success",
        };
    }

    if (/^account created\.\s*welcome/i.test(rawMessage)) {
        return {
            message: "Rupy: Account setup complete. Let's start tracking.",
            type: "success",
        };
    }

    return {
        message: rawMessage,
        type: rawType,
    };
}

function showRupyToast(message, category = "info", durationMs = null) {
    const mapped = mapRupyNotification(message, category);
    showAppToast(mapped.message, mapped.type, durationMs);
}

function triggerDeleteSuccessCelebration(message) {
    const overlay = document.querySelector("[data-delete-success-overlay]");
    if (!overlay) return;

    const lottieNode = overlay.querySelector("[data-delete-success-lottie]");
    const textNode = overlay.querySelector("[data-delete-success-text]");
    const animationPath = String(overlay.getAttribute("data-animation-path") || "").trim();

    if (textNode) {
        textNode.textContent = categoryDeleteCelebrationLabel(message);
    }

    let overlayClickHandler = null;
    let escapeHandler = null;

    const closeOverlay = () => {
        overlay.classList.remove("open");
        overlay.setAttribute("aria-hidden", "true");
        if (overlayClickHandler) {
            overlay.removeEventListener("click", overlayClickHandler);
            overlayClickHandler = null;
        }
        if (escapeHandler) {
            document.removeEventListener("keydown", escapeHandler);
            escapeHandler = null;
        }
        if (deleteSuccessTimer) {
            window.clearTimeout(deleteSuccessTimer);
            deleteSuccessTimer = null;
        }
        if (deleteSuccessAnim) {
            deleteSuccessAnim.destroy();
            deleteSuccessAnim = null;
        }
        if (lottieNode) {
            lottieNode.innerHTML = "";
        }
    };

    overlay.classList.add("open");
    overlay.setAttribute("aria-hidden", "false");
    deleteSuccessTimer = window.setTimeout(closeOverlay, 2500);

    escapeHandler = (event) => {
        if (event.key !== "Escape") return;
        closeOverlay();
    };
    overlayClickHandler = () => closeOverlay();
    document.addEventListener("keydown", escapeHandler);
    overlay.addEventListener("click", overlayClickHandler);

    if (!lottieNode || !animationPath) return;

    ensureLottieLoaded()
        .then((lottie) => {
            if (deleteSuccessAnim) {
                deleteSuccessAnim.destroy();
                deleteSuccessAnim = null;
            }

            lottieNode.innerHTML = "";
            deleteSuccessAnim = lottie.loadAnimation({
                container: lottieNode,
                renderer: "svg",
                loop: false,
                autoplay: true,
                path: animationPath,
                rendererSettings: {
                    preserveAspectRatio: "xMidYMid meet",
                },
            });

            if (deleteSuccessAnim) {
                deleteSuccessAnim.addEventListener("complete", () => {
                    if (!overlay.classList.contains("open")) return;
                    window.setTimeout(closeOverlay, 240);
                });
            }
        })
        .catch(() => {
            // Fall back to text-only confirmation if Lottie fails.
        });
}

function setupToastSystem() {
    toastContainer = document.querySelector("[data-toast-container]");
    if (!toastContainer) return;

    const flashedMessages = parseJsonScript("flashed-messages", []);
    if (!Array.isArray(flashedMessages) || !flashedMessages.length) return;

    const renderFlashedToasts = () => {
        flashedMessages.forEach((item) => {
            if (!Array.isArray(item) || item.length < 2) return;
            const [category, message] = item;
            showRupyToast(message, category);
        });
    };

    const deletedCategoryMessage = (() => {
        let latest = "";
        flashedMessages.forEach((item) => {
            if (!Array.isArray(item) || item.length < 2) return;
            const messageText = String(item[1] || "").trim();
            if (messageText.toLowerCase().includes("category deleted:")) {
                latest = messageText;
            }
        });
        return latest;
    })();

    const maybePlayDeleteCelebration = () => {
        if (!deletedCategoryMessage) return;
        triggerDeleteSuccessCelebration(deletedCategoryMessage);
    };

    if (splashRevealDelayMs > 0) {
        const startAfter = Math.max(0, splashRevealDelayMs - 120);
        window.setTimeout(renderFlashedToasts, startAfter);
        window.setTimeout(maybePlayDeleteCelebration, startAfter + 180);
        return;
    }

    renderFlashedToasts();
    window.setTimeout(maybePlayDeleteCelebration, 160);
}

function setupGoalUiEvent() {
    const eventPayload = parseJsonScript("goal-ui-event", null);
    if (!eventPayload || typeof eventPayload !== "object") return;

    const eventType = String(eventPayload.type || "").trim().toLowerCase();
    const message = String(eventPayload.message || "").trim();
    const toastType = normalizeToastType(eventPayload.toast_type || "info");
    if (!eventType || !message) return;

    showRupyToast(message, toastType, 3400);

    const eventTypeMap = {
        goal_created: "budget_planning",
        goal_completed: "saving_money",
        goal_deadline_warning: "high_spending",
        goal_archived: "idle",
        goal_deleted: "high_spending",
        goal_reactivated: "budget_planning",
        goal_recurring_reset: "budget_planning",
    };

    const mascotEventType = eventTypeMap[eventType];
    if (!mascotEventType) return;

    const emitEvent = () => {
        if (window.RupyMascot && typeof window.RupyMascot.emit === "function") {
            window.RupyMascot.emit(mascotEventType, { message });
            return;
        }
        window.dispatchEvent(new CustomEvent("rupy:event", {
            detail: {
                type: mascotEventType,
                message,
            },
        }));
    };

    window.setTimeout(emitEvent, 120);
}

window.showAppToast = showAppToast;
window.showRupyToast = showRupyToast;

function setupAppPageEntrance() {
    const body = document.body;
    if (!body) return;

    const hasLoginTransition = sessionStorage.getItem(LOGIN_TRANSITION_STORAGE_KEY) === "1";
    if (!body.classList.contains("auth-body") && hasLoginTransition) {
        body.classList.add("from-login-transition");
        sessionStorage.removeItem(LOGIN_TRANSITION_STORAGE_KEY);
    }

    if (prefersReducedMotion()) {
        body.classList.add("page-ready");
        return;
    }

    window.requestAnimationFrame(() => {
        body.classList.add("page-ready");
    });
}

function setupSplashIntro() {
    const rootNode = document.documentElement;
    const clearPreSplash = () => {
        if (rootNode) rootNode.classList.remove("pre-splash-login");
    };

    const splashNode = document.querySelector("[data-splash]");
    if (!splashNode) {
        clearPreSplash();
        return;
    }

    const splashShell = splashNode.querySelector(".splash-shell");
    const sidebarBrand = document.querySelector(".sidebar-brand");
    const canDockToSidebar = Boolean(
        splashShell && sidebarBrand && !document.body.classList.contains("auth-body")
    );

    const forcedByLogin = sessionStorage.getItem(SPLASH_FORCE_STORAGE_KEY) === "1";
    const hasSeenSplash = sessionStorage.getItem(SPLASH_SEEN_STORAGE_KEY) === "1";
    const shouldShowSplash = !prefersReducedMotion() && (forcedByLogin || !hasSeenSplash);

    const removeSplash = () => {
        splashNode.remove();
        document.body.classList.remove("splash-active");
        document.body.classList.remove("splash-docking");
        clearPreSplash();
    };

    if (!shouldShowSplash) {
        sessionStorage.removeItem(SPLASH_FORCE_STORAGE_KEY);
        splashRevealDelayMs = 0;
        removeSplash();
        return;
    }

    splashRevealDelayMs = 2850;
    sessionStorage.setItem(SPLASH_SEEN_STORAGE_KEY, "1");
    sessionStorage.removeItem(SPLASH_FORCE_STORAGE_KEY);
    splashNode.hidden = false;

    document.body.classList.add("splash-active");
    if (canDockToSidebar) {
        document.body.classList.add("splash-docking");
    }

    window.requestAnimationFrame(() => {
        splashNode.classList.add("show");
    });

    if (canDockToSidebar) {
        const applyDockTarget = () => {
            const shellRect = splashShell.getBoundingClientRect();
            const brandRect = sidebarBrand.getBoundingClientRect();
            if (!shellRect.width || !brandRect.width) return;

            const shellCenterX = shellRect.left + (shellRect.width / 2);
            const shellCenterY = shellRect.top + (shellRect.height / 2);
            const brandCenterX = brandRect.left + (brandRect.width / 2);
            const brandCenterY = brandRect.top + (brandRect.height / 2);

            const offsetX = brandCenterX - shellCenterX;
            const offsetY = brandCenterY - shellCenterY;
            const dockScale = Math.max(0.32, Math.min(0.46, brandRect.width / shellRect.width));

            splashNode.style.setProperty("--splash-dock-x", `${offsetX.toFixed(1)}px`);
            splashNode.style.setProperty("--splash-dock-y", `${offsetY.toFixed(1)}px`);
            splashNode.style.setProperty("--splash-dock-scale", dockScale.toFixed(3));
        };

        window.setTimeout(applyDockTarget, 720);
        window.setTimeout(() => {
            splashNode.classList.add("dock");
        }, 1760);

        window.setTimeout(() => {
            document.body.classList.remove("splash-docking");
        }, 2360);
    }

    window.setTimeout(() => {
        splashNode.classList.add("hide");
    }, 2480);

    window.setTimeout(() => {
        removeSplash();
    }, splashRevealDelayMs);
}

function setupAuthLoginFlow() {
    const loginForm = document.querySelector("form.auth-form[data-login-form]");
    if (!loginForm) return;

    const submitButton = loginForm.querySelector('button[type="submit"]');
    const signInDelayMs = 700;
    let isSubmitting = false;

    loginForm.addEventListener("submit", (event) => {
        if (isSubmitting) return;
        isSubmitting = true;
        event.preventDefault();

        sessionStorage.setItem(LOGIN_TRANSITION_STORAGE_KEY, "1");

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add("is-loading");
            submitButton.innerHTML = `
                <span class="btn-spinner" aria-hidden="true"></span>
                <span>Signing in...</span>
            `;
        }

        if (!prefersReducedMotion()) {
            document.body.classList.add("page-exit");
        }

        window.setTimeout(() => {
            loginForm.submit();
        }, signInDelayMs);
    });
}

function setupLoginRupyMascot() {
    const loginRoot = document.querySelector("[data-rupy-auth], [data-rupy-login]");
    if (!loginRoot) return;

    const mascotNode = loginRoot.querySelector("[data-rupy-mascot]");
    const formNode = loginRoot.querySelector("form.auth-form");
    if (!mascotNode || !formNode) return;

    const statusNode = loginRoot.querySelector("[data-rupy-status]");
    const mouthNode = mascotNode.querySelector("[data-rupy-mouth]");
    const leftBrowNode = mascotNode.querySelector("[data-rupy-brow-left]");
    const rightBrowNode = mascotNode.querySelector("[data-rupy-brow-right]");
    const nameInput = formNode.querySelector('input[data-rupy-track="name"], input[name="name"]');
    const emailInput = formNode.querySelector('input[data-rupy-track="email"], input[type="email"]');
    const passwordInput = formNode.querySelector('input[data-rupy-track="password"], input[name="password"]');
    const confirmPasswordInput = formNode.querySelector('input[data-rupy-track="confirm_password"], input[name="confirm_password"]');
    const passwordToggles = Array.from(formNode.querySelectorAll("[data-password-toggle]"));
    const formModeRaw = String(formNode.getAttribute("data-rupy-form") || (formNode.hasAttribute("data-login-form") ? "login" : "register")).trim().toLowerCase();
    const formMode = formModeRaw === "register" ? "register" : "login";
    const mascotImageNode = mascotNode.querySelector("[data-rupy-image]");
    const imageStateMap = mascotImageNode
        ? {
            idle: String(mascotNode.dataset.rupyImgIdle || mascotImageNode.getAttribute("src") || "").trim(),
            thinking: String(mascotNode.dataset.rupyImgThinking || "").trim(),
            warning: String(mascotNode.dataset.rupyImgWarning || "").trim(),
            confused: String(mascotNode.dataset.rupyImgConfused || "").trim(),
            error: String(mascotNode.dataset.rupyImgError || "").trim(),
            celebrate: String(mascotNode.dataset.rupyImgCelebrate || "").trim(),
            proud: String(mascotNode.dataset.rupyImgProud || "").trim(),
        }
        : null;
    const imageFallback = imageStateMap?.idle || "";
    const imageStateLookup = (stateName) => {
        const normalized = String(stateName || "").trim().toLowerCase();
        if (!imageStateMap) return "";
        if (normalized === "thinking" || normalized === "focus" || normalized === "peek") {
            return imageStateMap.thinking || imageFallback;
        }
        if (normalized === "warning" || normalized === "confused") {
            return imageStateMap.confused || imageStateMap.warning || imageStateMap.error || imageFallback;
        }
        if (normalized === "error" || normalized === "sleep") {
            return imageStateMap.error || imageStateMap.warning || imageFallback;
        }
        if (normalized === "success" || normalized === "wave") {
            return imageStateMap.proud || imageStateMap.celebrate || imageFallback;
        }
        if (normalized === "celebrate") {
            return imageStateMap.celebrate || imageStateMap.proud || imageFallback;
        }
        return imageFallback;
    };
    const setImageForState = (stateName) => {
        if (!mascotImageNode || !imageStateMap) return;
        const nextImage = imageStateLookup(stateName);
        if (!nextImage) return;
        const currentImage = String(mascotImageNode.getAttribute("src") || "").trim();
        if (currentImage === nextImage) return;
        mascotImageNode.setAttribute("src", nextImage);
    };

    if (mascotImageNode) {
        mascotImageNode.addEventListener("error", () => {
            mascotNode.removeAttribute("data-rupy-has-images");
        });
    }

    if (imageStateMap) {
        const preloadSet = new Set(Object.values(imageStateMap).filter(Boolean));
        preloadSet.forEach((src) => {
            const preloadImage = new Image();
            preloadImage.src = src;
        });
    }

    const faceMap = {
        neutral: {
            mouth: "M136 181 Q160 188 184 181",
            leftBrow: "M118 123 Q133 111 147 122",
            rightBrow: "M172 122 Q186 111 203 122",
        },
        grin: {
            mouth: "M132 177 Q160 198 188 177",
            leftBrow: "M118 123 Q133 111 147 122",
            rightBrow: "M172 122 Q186 111 203 122",
        },
        focus: {
            mouth: "M136 181 Q160 191 184 181",
            leftBrow: "M118 125 Q132 116 147 124",
            rightBrow: "M172 124 Q186 116 203 125",
        },
        concern: {
            mouth: "M136 186 Q160 170 184 186",
            leftBrow: "M118 124 Q132 113 147 121",
            rightBrow: "M172 121 Q186 113 203 124",
        },
    };

    const setFace = (faceKey) => {
        const nextFace = faceMap[faceKey] || faceMap.neutral;
        if (mouthNode && nextFace.mouth) mouthNode.setAttribute("d", nextFace.mouth);
        if (leftBrowNode && nextFace.leftBrow) leftBrowNode.setAttribute("d", nextFace.leftBrow);
        if (rightBrowNode && nextFace.rightBrow) rightBrowNode.setAttribute("d", nextFace.rightBrow);
    };

    const setStatus = (text) => {
        if (!statusNode) return;
        const message = String(text || "").trim();
        if (!message) return;
        statusNode.textContent = message;
    };

    const setLook = (x, y = 0) => {
        mascotNode.style.setProperty("--rupy-look-x", `${clampNumber(x, -7, 7)}px`);
        mascotNode.style.setProperty("--rupy-look-y", `${clampNumber(y, -6, 6)}px`);
    };

    const rupyMachine = createRupyStateMachine(mascotNode, {
        classPrefix: "state-",
        initialState: "idle",
        cooldownMs: 220,
    });
    let cancelStateSequence = null;
    const setState = (stateName, options = {}) => {
        const normalized = String(stateName || "").replace(/^state-/, "").trim().toLowerCase() || "idle";
        rupyMachine.transition(normalized, options);
        setImageForState(normalized);
        if (options.face) setFace(options.face);
        if (typeof options.lookX === "number" || typeof options.lookY === "number") {
            setLook(options.lookX || 0, options.lookY || 0);
        }
        if (options.status) setStatus(options.status);
    };
    const playStateSequence = (steps) => {
        if (cancelStateSequence) cancelStateSequence();
        cancelStateSequence = runRupyStateSequence(setState, steps);
    };

    const triggerWink = () => {
        mascotNode.classList.remove("is-wink");
        if (prefersReducedMotion()) return;
        void mascotNode.offsetWidth;
        mascotNode.classList.add("is-wink");
        window.setTimeout(() => mascotNode.classList.remove("is-wink"), 220);
    };

    let blinkTimer = null;
    const clearBlinkTimer = () => {
        if (!blinkTimer) return;
        window.clearTimeout(blinkTimer);
        blinkTimer = null;
    };
    const blinkNow = () => {
        mascotNode.classList.remove("is-blink");
        if (prefersReducedMotion()) return;
        void mascotNode.offsetWidth;
        mascotNode.classList.add("is-blink");
        window.setTimeout(() => mascotNode.classList.remove("is-blink"), 150);
    };
    const scheduleBlink = () => {
        clearBlinkTimer();
        if (prefersReducedMotion()) return;
        const nextBlinkInMs = 2300 + Math.floor(Math.random() * 1700);
        blinkTimer = window.setTimeout(() => {
            blinkNow();
            scheduleBlink();
        }, nextBlinkInMs);
    };

    const hasServerError = Boolean(loginRoot.querySelector(".auth-error, .field-error"));
    if (hasServerError) {
        playStateSequence([
            {
                state: "thinking",
                delayMs: 180,
                options: {
                    face: "focus",
                    status: "Checking what went wrong...",
                    lookX: 0,
                    lookY: 0,
                },
            },
            {
                state: "error",
                options: {
                    face: "concern",
                    status: formMode === "register"
                        ? "There is an issue in the form. Please review and try again."
                        : "The details did not match. Please check and try again.",
                    lookX: 0,
                    lookY: 0,
                },
            },
        ]);
    } else {
        playStateSequence([
            {
                state: "wave",
                delayMs: prefersReducedMotion() ? 0 : 1600,
                options: {
                    face: "grin",
                    status: formMode === "register"
                        ? "Hi, I am Rupy. Let's create your account."
                        : "Hi, I am Rupy. Let's get you signed in.",
                    lookX: 0,
                    lookY: 0,
                },
            },
            {
                state: "idle",
                options: {
                    face: "neutral",
                    status: formMode === "register"
                        ? "Start with your name and email. I will guide you."
                        : "Enter your email and password. I will guide you.",
                    lookX: 0,
                    lookY: 0,
                },
            },
        ]);
    }

    if (nameInput) {
        nameInput.addEventListener("focus", () => {
            setState("state-focus", {
                face: "grin",
                status: "Great. Enter your full name.",
                lookX: -2,
                lookY: -1,
            });
        });

        nameInput.addEventListener("input", () => {
            const value = String(nameInput.value || "");
            setLook(clampNumber(-2 + (value.length * 0.18), -2, 4), -1);
            if (!value.trim()) {
                setStatus("Your name helps personalize your dashboard.");
                return;
            }
            if (value.trim().length < 3) {
                setStatus("Add your full name for a better profile.");
                return;
            }
            setStatus("Nice. Your profile name looks good.");
        });

        nameInput.addEventListener("blur", () => {
            setState("state-idle", {
                face: "neutral",
                status: "Good start. Continue with your email.",
                lookX: 0,
                lookY: 0,
            });
        });
    }

    if (emailInput) {
        emailInput.addEventListener("focus", () => {
            setState("state-focus", {
                face: "focus",
                status: formMode === "register"
                    ? "Use an active email address."
                    : "Perfect. Start with your email.",
                lookX: 4,
                lookY: -1,
            });
        });

        emailInput.addEventListener("input", () => {
            const value = String(emailInput.value || "");
            const lookOffset = clampNumber(2 + (value.length * 0.34), 2, 7);
            setLook(lookOffset, -1);
            if (!value.trim()) {
                setStatus("Email field is empty.");
                return;
            }
            if (value.includes("@") && value.includes(".")) {
                setStatus(formMode === "register"
                    ? "That email looks valid. Now create a password."
                    : "That email looks valid. Now enter your password.");
                return;
            }
            setStatus("Complete the email to continue.");
        });

        emailInput.addEventListener("blur", () => {
            setState("state-idle", {
                face: "neutral",
                status: formMode === "register"
                    ? "Nice. Next, create your password."
                    : "Nice. Move to the password field.",
                lookX: 0,
                lookY: 0,
            });
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener("focus", () => {
            setState("state-peek", {
                face: "focus",
                status: formMode === "register"
                    ? "Create a secure password. I never peek."
                    : "Your password is secure. I never peek.",
                lookX: 5,
                lookY: 1,
            });
            triggerWink();
        });

        passwordInput.addEventListener("input", () => {
            const value = String(passwordInput.value || "");
            setLook(clampNumber(1 + (value.length * 0.22), 1, 6), 1);
            if (value.length === 0) {
                setStatus("Enter your password to unlock the vault.");
                return;
            }
            if (value.length < 6) {
                setStatus("Use a stronger password.");
                return;
            }
            setState("state-success", {
                face: "grin",
                status: formMode === "register"
                    ? "Looks strong. Confirm it once."
                    : "Looks strong. Login is ready.",
                lookX: 1,
                lookY: 0,
            });
        });

        passwordInput.addEventListener("blur", () => {
            setState("state-idle", {
                face: "neutral",
                status: formMode === "register"
                    ? "Almost done. Confirm password and create account."
                    : "All set. Press the login button.",
                lookX: 0,
                lookY: 0,
            });
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener("focus", () => {
            setState("state-focus", {
                face: "focus",
                status: "Re-enter password to confirm.",
                lookX: 4,
                lookY: 1,
            });
        });

        confirmPasswordInput.addEventListener("input", () => {
            const confirmValue = String(confirmPasswordInput.value || "");
            const passwordValue = String(passwordInput?.value || "");
            if (!confirmValue) {
                setStatus("Confirm your password to finish account setup.");
                return;
            }
            if (passwordValue && confirmValue !== passwordValue) {
                setState("state-warning", {
                    face: "concern",
                    status: "Passwords do not match yet.",
                    lookX: 0,
                    lookY: 0,
                });
                return;
            }
            setState("state-celebrate", {
                face: "grin",
                status: "Perfect match. You can create your account now.",
                lookX: 0,
                lookY: 0,
            });
        });

        confirmPasswordInput.addEventListener("blur", () => {
            setState("state-idle", {
                face: "neutral",
                status: "Everything looks good. Submit when ready.",
                lookX: 0,
                lookY: 0,
            });
        });
    }

    passwordToggles.forEach((toggle) => {
        toggle.addEventListener("click", () => {
            setState("state-peek", {
                face: "grin",
                status: "Visibility changed. Your password is still safe.",
                lookX: 4,
                lookY: 1,
            });
            triggerWink();
        });
    });

    formNode.addEventListener("submit", () => {
        clearBlinkTimer();
        if (cancelStateSequence) cancelStateSequence();
        playStateSequence([
            {
                state: "thinking",
                options: {
                    face: "focus",
                    status: formMode === "register"
                        ? "Creating your account..."
                        : "Verifying your credentials...",
                    lookX: 0,
                    lookY: 0,
                },
            },
        ]);
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            clearBlinkTimer();
            if (cancelStateSequence) cancelStateSequence();
            setState("state-sleep", {
                face: "neutral",
                status: "I will rest until you are back.",
                lookX: 0,
                lookY: 0,
            });
            return;
        }
        setState("state-idle", {
            face: "neutral",
            status: formMode === "register"
                ? "Welcome back. Continue creating your account."
                : "Welcome back. Continue your login.",
            lookX: 0,
            lookY: 0,
        });
        scheduleBlink();
    });

    scheduleBlink();
}

function setupProfileDropdown() {
    const menu = document.querySelector("[data-profile-menu]");
    if (!menu) return;

    const toggle = menu.querySelector("[data-profile-toggle]");
    const dropdown = menu.querySelector("[data-profile-dropdown]");
    if (!toggle || !dropdown) return;

    const getMenuItems = () => {
        return Array.from(dropdown.querySelectorAll("[data-profile-item]"))
            .filter((item) => !item.hasAttribute("disabled"));
    };

    const setMenuItemsTabIndex = (isOpen) => {
        getMenuItems().forEach((item) => {
            item.tabIndex = isOpen ? 0 : -1;
        });
    };

    const closeMenu = ({ returnFocus = false } = {}) => {
        menu.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        setMenuItemsTabIndex(false);
        if (returnFocus) {
            toggle.focus();
        }
    };

    const focusMenuItem = (index) => {
        const items = getMenuItems();
        if (!items.length) return;
        const normalizedIndex = ((index % items.length) + items.length) % items.length;
        items[normalizedIndex].focus();
    };

    const openMenu = ({ focusTarget = "none" } = {}) => {
        menu.classList.add("open");
        toggle.setAttribute("aria-expanded", "true");
        setMenuItemsTabIndex(true);

        if (focusTarget === "first") {
            window.requestAnimationFrame(() => {
                focusMenuItem(0);
            });
            return;
        }

        if (focusTarget === "last") {
            window.requestAnimationFrame(() => {
                const items = getMenuItems();
                if (!items.length) return;
                items[items.length - 1].focus();
            });
        }
    };

    toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        if (menu.classList.contains("open")) {
            closeMenu();
            return;
        }
        openMenu();
    });

    toggle.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openMenu({ focusTarget: "first" });
            return;
        }

        if (event.key === "ArrowUp") {
            event.preventDefault();
            openMenu({ focusTarget: "last" });
        }
    });

    dropdown.addEventListener("click", (event) => {
        event.stopPropagation();
    });

    dropdown.addEventListener("keydown", (event) => {
        if (!menu.classList.contains("open")) return;

        const items = getMenuItems();
        if (!items.length) return;

        const activeIndex = items.indexOf(document.activeElement);
        if (event.key === "ArrowDown") {
            event.preventDefault();
            focusMenuItem(activeIndex + 1);
            return;
        }

        if (event.key === "ArrowUp") {
            event.preventDefault();
            focusMenuItem(activeIndex - 1);
            return;
        }

        if (event.key === "Home") {
            event.preventDefault();
            focusMenuItem(0);
            return;
        }

        if (event.key === "End") {
            event.preventDefault();
            focusMenuItem(items.length - 1);
            return;
        }

        if (event.key === "Escape") {
            event.preventDefault();
            closeMenu({ returnFocus: true });
        }
    });

    document.addEventListener("click", (event) => {
        if (!menu.contains(event.target)) closeMenu();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.classList.contains("open")) {
            closeMenu({ returnFocus: true });
        }
    });

    document.addEventListener("focusin", (event) => {
        if (!menu.classList.contains("open")) return;
        if (!menu.contains(event.target)) {
            closeMenu();
        }
    });

    setMenuItemsTabIndex(false);
}

function setupAppearanceQuickControls() {
    const body = document.body;
    const html = document.documentElement;
    if (!body || !html) return;

    const themeSelect = document.querySelector("[data-appearance-theme]");
    const languageSelect = document.querySelector("[data-appearance-language]");
    if (!themeSelect && !languageSelect) return;

    const knownThemes = ["default", "midnight", "forest"];
    const knownLanguages = ["en", "hi"];

    const readCurrentTheme = () => {
        const selectedValue = String(themeSelect?.value || body.dataset.theme || "default").trim().toLowerCase();
        return knownThemes.includes(selectedValue) ? selectedValue : "default";
    };

    const readCurrentLanguage = () => {
        const selectedValue = String(languageSelect?.value || body.dataset.language || "en").trim().toLowerCase();
        return knownLanguages.includes(selectedValue) ? selectedValue : "en";
    };

    const applyAppearance = ({ theme, language }) => {
        const finalTheme = knownThemes.includes(theme) ? theme : "default";
        const finalLanguage = knownLanguages.includes(language) ? language : "en";

        body.dataset.theme = finalTheme;
        body.dataset.language = finalLanguage;
        body.classList.remove("theme-default", "theme-midnight", "theme-forest");
        body.classList.add(`theme-${finalTheme}`);
        body.classList.remove("lang-en", "lang-hi");
        body.classList.add(`lang-${finalLanguage}`);
        html.lang = finalLanguage === "hi" ? "hi" : "en";
    };

    const persistAppearance = async ({ theme, language }) => {
        // VIVA: FRONTEND API - save theme and language preferences to the backend.
        const response = await fetch("/ui/preferences/appearance", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                theme,
                language,
            }),
        });
        if (!response.ok) {
            throw new Error("Could not save appearance preferences");
        }
        const payload = await response.json().catch(() => ({}));
        const savedTheme = String(payload.theme || theme || "default").trim().toLowerCase();
        const savedLanguage = String(payload.language || language || "en").trim().toLowerCase();
        return {
            theme: knownThemes.includes(savedTheme) ? savedTheme : "default",
            language: knownLanguages.includes(savedLanguage) ? savedLanguage : "en",
        };
    };

    let isSaving = false;
    const handlePreferenceChange = async () => {
        if (isSaving) return;

        const previousTheme = body.dataset.theme || "default";
        const previousLanguage = body.dataset.language || "en";
        const nextTheme = readCurrentTheme();
        const nextLanguage = readCurrentLanguage();
        const shouldReloadForLanguage = nextLanguage !== previousLanguage;

        isSaving = true;
        if (themeSelect) themeSelect.disabled = true;
        if (languageSelect) languageSelect.disabled = true;
        applyAppearance({ theme: nextTheme, language: nextLanguage });

        try {
            const saved = await persistAppearance({
                theme: nextTheme,
                language: nextLanguage,
            });
            applyAppearance(saved);
            if (themeSelect) themeSelect.value = saved.theme;
            if (languageSelect) languageSelect.value = saved.language;
            showRupyToast("Appearance preferences updated.", "success", 2200);
            if (shouldReloadForLanguage) {
                window.setTimeout(() => {
                    window.location.reload();
                }, 260);
            }
        } catch (_) {
            applyAppearance({
                theme: previousTheme,
                language: previousLanguage,
            });
            if (themeSelect) themeSelect.value = previousTheme;
            if (languageSelect) languageSelect.value = previousLanguage;
            showRupyToast("Could not save appearance. Please retry.", "error");
        } finally {
            isSaving = false;
            if (themeSelect) themeSelect.disabled = false;
            if (languageSelect) languageSelect.disabled = false;
        }
    };

    if (themeSelect) {
        themeSelect.addEventListener("change", () => {
            void handlePreferenceChange();
        });
    }
    if (languageSelect) {
        languageSelect.addEventListener("change", () => {
            void handlePreferenceChange();
        });
    }
}

function setupLanguageLocalization() {
    if (uiLanguage() !== "hi") return;
    if (!document.body) return;

    const textReplacements = {
        "Dashboard": "डैशबोर्ड",
        "Expenses": "खर्च",
        "Reports": "रिपोर्ट्स",
        "Goals": "लक्ष्य",
        "Gamification": "गेमिफिकेशन",
        "Settings": "सेटिंग्स",
        "My Account": "मेरा अकाउंट",
        "Logout": "लॉगआउट",
        "This Month": "इस माह",
        "All Time": "सभी समय",
        "Notifications": "नोटिफिकेशन्स",
        "Mark all as read": "सभी को पढ़ा हुआ चिह्नित करें",
        "Mark as read": "पढ़ा हुआ चिह्नित करें",
        "No notifications yet.": "अभी कोई नोटिफिकेशन नहीं है।",
        "No notifications in this section.": "इस सेक्शन में कोई नोटिफिकेशन नहीं है।",
        "Quick Search": "क्विक सर्च",
        "Recent Searches": "हाल की खोजें",
        "Suggested Searches": "सुझाई गई खोजें",
        "Recent transactions": "हाल के ट्रांजैक्शन",
        "Load more results": "और परिणाम लोड करें",
        "Open full transaction list": "पूरी ट्रांजैक्शन सूची खोलें",
        "Search Results": "सर्च परिणाम",
        "No matching transactions found.": "कोई मैचिंग ट्रांजैक्शन नहीं मिला।",
        "Search failed. Please retry.": "सर्च असफल रहा। कृपया फिर कोशिश करें।",
        "This Month Summary": "इस माह का सारांश",
        "All Time Summary": "सभी समय का सारांश",
        "Budget Summary": "बजट सारांश",
        "Monthly Budget Status": "मासिक बजट स्थिति",
        "Smart Anomaly Alerts": "स्मार्ट एनोमली अलर्ट",
        "Attention Needed": "ध्यान आवश्यक",
        "Normal Pattern": "सामान्य पैटर्न",
        "Within budget": "बजट के भीतर",
        "No spending yet": "अभी खर्च नहीं हुआ",
        "No budget set": "कोई बजट सेट नहीं है",
        "Rollover": "रोलओवर",
        "Carry next:": "अगले माह ले जाएँ:",
        "Alert threshold:": "अलर्ट थ्रेशहोल्ड:",
        "Tune alerts & budget": "अलर्ट और बजट सेट करें",
        "Total Expense": "कुल खर्च",
        "Total Income": "कुल आय",
        "Remaining Balance": "शेष बैलेंस",
        "Effective Budget": "प्रभावी बजट",
        "Spent This Month": "इस माह खर्च",
        "Budget Left": "बचा हुआ बजट",
        "Add New Expense": "नया खर्च जोड़ें",
        "Add Expense": "खर्च जोड़ें",
        "Add Income": "आय जोड़ें",
        "History Filter": "इतिहास फ़िल्टर",
        "Expense History": "खर्च इतिहास",
        "Income History": "आय इतिहास",
        "Category": "श्रेणी",
        "Description": "विवरण",
        "Date": "तारीख",
        "Time": "समय",
        "Action": "क्रिया",
        "Edit": "संपादित करें",
        "Delete": "हटाएं",
        "Set Monthly Budget": "मासिक बजट सेट करें",
        "Carry Forward Preview": "कैरी फ़ॉरवर्ड पूर्वावलोकन",
        "Existing Categories": "मौजूदा श्रेणियां",
        "Category Name": "श्रेणी नाम",
        "Save Budget": "बजट सेव करें",
        "Expense Overview": "खर्च अवलोकन",
        "Monthly Spending Breakdown": "मासिक खर्च का विवरण",
        "Category Split": "श्रेणी विभाजन",
        "Total Spent": "कुल खर्च",
        "Budget Left": "बचा हुआ बजट",
        "My Account": "मेरा अकाउंट",
        "Profile Details": "प्रोफाइल विवरण",
        "Full Name": "पूरा नाम",
        "Email Address": "ईमेल पता",
        "Avatar Style": "अवतार शैली",
        "Save Profile": "प्रोफाइल सेव करें",
        "Security": "सुरक्षा",
        "Current Password": "वर्तमान पासवर्ड",
        "New Password": "नया पासवर्ड",
        "Confirm New Password": "नए पासवर्ड की पुष्टि",
        "Update Password": "पासवर्ड अपडेट करें",
        "Confirm Logout": "लॉगआउट पुष्टि",
        "Confirm Action": "क्रिया की पुष्टि",
        "Rupy Gamification Hub": "रुपी गेमिफिकेशन हब",
        "Track savings targets and spending limits from one place.": "सेविंग और खर्च सीमा के लक्ष्यों को एक ही जगह ट्रैक करें।",
        "Create New Goal": "नया लक्ष्य बनाएं",
        "Custom (no template)": "कस्टम (बिना टेम्पलेट)",
        "Active Goals": "सक्रिय लक्ष्य",
        "Completed Goals": "पूर्ण लक्ष्य",
        "Archived Goals": "संग्रहीत लक्ष्य",
        "Recurring monthly reset (for spending cap goals)": "मासिक रीसेट (स्पेंडिंग कैप लक्ष्यों के लिए)",
        "No active goals right now.": "अभी कोई सक्रिय लक्ष्य नहीं है।",
        "Back to Dashboard": "डैशबोर्ड पर वापस जाएं",
        "Mark Complete": "पूर्ण करें",
        "Move to Active": "सक्रिय में लाएं",
        "Restore": "पुनर्स्थापित करें",
        "Open Full Badge Center": "पूरा बैज सेंटर खोलें",
        "Daily Challenge": "डेली चैलेंज",
        "Unlocked Achievements": "अनलॉक्ड अचीवमेंट्स",
        "Locked Achievements": "लॉक्ड अचीवमेंट्स",
        "XP Rules": "XP नियम",
        "Create shareable finance memes": "शेयर करने योग्य फाइनेंस मीम बनाएं",
        "Generate Meme": "मीम बनाएं",
        "Download PNG": "PNG डाउनलोड करें",
        "Share Meme": "मीम शेयर करें",
        "Do you want to logout from ExpensePro?": "क्या आप ExpensePro से लॉगआउट करना चाहते हैं?",
        "Are you sure you want to continue?": "क्या आप जारी रखना चाहते हैं?",
        "Cancel": "रद्द करें",
        "Yes, continue": "हाँ, जारी रखें",
    };

    const placeholderReplacements = {
        "Search merchant / category / date / amount...": "merchant / category / date / amount खोजें...",
        "Amount (INR)": "राशि (INR)",
        "Income Amount (INR)": "आय राशि (INR)",
        "Description": "विवरण",
        "Source (Salary, Freelance, etc.)": "स्रोत (Salary, Freelance, आदि)",
        "Budget amount (INR)": "बजट राशि (INR)",
        "Email address": "ईमेल पता",
        "Password": "पासवर्ड",
        "Full name": "पूरा नाम",
        "Password (minimum 6 chars)": "पासवर्ड (कम से कम 6 अक्षर)",
        "Confirm password": "पासवर्ड पुष्टि करें",
        "Enter current password": "वर्तमान पासवर्ड दर्ज करें",
        "At least 6 characters": "कम से कम 6 अक्षर",
        "Re-enter new password": "नया पासवर्ड फिर से दर्ज करें",
    };

    const ariaReplacements = {
        "Open profile menu": "प्रोफाइल मेनू खोलें",
        "Search (Ctrl+K)": "खोजें (Ctrl+K)",
        "Notifications": "नोटिफिकेशन्स",
        "Close notifications": "नोटिफिकेशन्स बंद करें",
        "Close search": "सर्च बंद करें",
        "Search transactions": "ट्रांजैक्शन खोजें",
        "Select month": "माह चुनें",
        "Toggle sidebar": "साइडबार टॉगल करें",
    };

    const excludedTags = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "CODE", "PRE", "TEXTAREA"]);
    const replacementEntries = Object.entries(textReplacements).sort((a, b) => b[0].length - a[0].length);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            if (!node || !node.parentElement) return NodeFilter.FILTER_REJECT;
            if (excludedTags.has(node.parentElement.tagName)) return NodeFilter.FILTER_REJECT;
            const text = String(node.nodeValue || "");
            if (!text.trim()) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
        },
    });

    const textNodes = [];
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    textNodes.forEach((node) => {
        const rawText = String(node.nodeValue || "");
        let translated = rawText;
        replacementEntries.forEach(([sourceText, targetText]) => {
            if (!translated.includes(sourceText)) return;
            translated = translated.split(sourceText).join(targetText);
        });
        if (translated !== rawText) {
            node.nodeValue = translated;
        }
    });

    document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((field) => {
        const original = String(field.getAttribute("placeholder") || "");
        const next = placeholderReplacements[original];
        if (next) {
            field.setAttribute("placeholder", next);
        }
    });

    document.querySelectorAll("[aria-label]").forEach((node) => {
        const original = String(node.getAttribute("aria-label") || "");
        const next = ariaReplacements[original];
        if (next) {
            node.setAttribute("aria-label", next);
        }
    });
}

function setupAccountAvatarPreview() {
    const previewNode = document.querySelector("[data-account-avatar-preview]");
    if (!previewNode) return;

    const imageInput = document.querySelector("[data-account-image-input]");
    const removeToggle = document.querySelector("[data-account-image-remove]");
    const removeToggleWrap = removeToggle ? removeToggle.closest(".account-avatar-remove-toggle") : null;
    const imageNameNode = document.querySelector("[data-account-image-filename]");
    const imageStatusNode = document.querySelector("[data-account-image-status]");
    const accountForm = document.querySelector("[data-account-form]");
    const imageSaveUrl = String(accountForm?.getAttribute("data-account-image-save-url") || "/account/profile-image");
    const croppedDataField = document.querySelector("[data-account-cropped-data]");
    const imagePickers = document.querySelectorAll("[data-account-image-trigger]");
    const cropModal = document.querySelector("[data-account-crop-modal]");
    const cropCanvas = document.querySelector("[data-account-crop-canvas]");
    const cropZoom = document.querySelector("[data-account-crop-zoom]");
    const cropApplyButton = document.querySelector("[data-account-crop-apply]");
    const cropCancelButtons = document.querySelectorAll("[data-account-crop-cancel]");
    const viewButton = document.querySelector("[data-account-image-view]");
    const viewModal = document.querySelector("[data-account-view-modal]");
    const viewImageNode = document.querySelector("[data-account-view-image]");
    const viewEmptyNode = document.querySelector("[data-account-view-empty]");
    const viewCloseButtons = document.querySelectorAll("[data-account-view-close]");
    const initialNode = previewNode.querySelector("[data-account-avatar-initial]");
    let imageNode = previewNode.querySelector("[data-account-avatar-image]");

    const presetInputs = document.querySelectorAll("[data-avatar-preset-input]");

    let persistedImageSrc = imageNode ? String(imageNode.getAttribute("src") || "").trim() : "";
    let activeViewImageSrc = persistedImageSrc;
    const defaultImageName = imageNameNode ? String(imageNameNode.textContent || "").trim() : "No file selected";
    const maxBytesFromMarkup = Number.parseInt(String(imageInput?.getAttribute("data-account-image-max-bytes") || ""), 10);
    const maxUploadBytes = Number.isFinite(maxBytesFromMarkup) && maxBytesFromMarkup > 0
        ? maxBytesFromMarkup
        : (20 * 1024 * 1024);
    const cropCtx = cropCanvas ? cropCanvas.getContext("2d") : null;
    let previewImageUrl = "";
    let cropObjectUrl = "";
    const cropState = {
        image: null,
        scale: 1,
        minScale: 1,
        offsetX: 0,
        offsetY: 0,
        dragging: false,
        pointerId: null,
        startX: 0,
        startY: 0,
    };

    const updateQuickButtonLabel = (hasImage) => {
        imagePickers.forEach((button) => {
            const labelNode = button.querySelector("span");
            if (!labelNode) return;
            const uploadLabel = String(button.getAttribute("data-label-upload") || "Upload Profile Photo");
            const changeLabel = String(button.getAttribute("data-label-change") || "Change Profile Photo");
            labelNode.textContent = hasImage ? changeLabel : uploadLabel;
        });
    };

    const setImageName = (nameValue) => {
        if (!imageNameNode) return;
        const cleanName = String(nameValue || "").trim();
        imageNameNode.textContent = cleanName || defaultImageName;
    };

    const setImageStatus = (message, { error = false, hidden = false } = {}) => {
        if (!imageStatusNode) return;
        if (hidden) {
            imageStatusNode.hidden = true;
            imageStatusNode.textContent = "";
            imageStatusNode.classList.remove("error");
            return;
        }
        const text = String(message || "").trim();
        imageStatusNode.textContent = text;
        imageStatusNode.hidden = !text;
        imageStatusNode.classList.toggle("error", Boolean(error));
    };

    const setViewAvailability = (isEnabled) => {
        previewNode.classList.toggle("can-view", Boolean(isEnabled));
        if (isEnabled) {
            previewNode.setAttribute("tabindex", "0");
            previewNode.setAttribute("role", "button");
            previewNode.setAttribute("aria-label", "View profile photo");
        } else {
            previewNode.removeAttribute("tabindex");
            previewNode.removeAttribute("role");
            previewNode.removeAttribute("aria-label");
        }
        if (viewButton) {
            viewButton.disabled = !isEnabled;
            viewButton.classList.toggle("is-disabled", !isEnabled);
        }
        if (viewImageNode) {
            viewImageNode.hidden = !isEnabled;
        }
        if (viewEmptyNode) {
            viewEmptyNode.hidden = Boolean(isEnabled);
        }
    };

    const closeViewModal = () => {
        if (!viewModal) return;
        viewModal.classList.remove("open");
        viewModal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("account-view-open");
    };

    const openViewModal = () => {
        if (!viewModal || !activeViewImageSrc) return;
        if (viewImageNode) {
            viewImageNode.src = activeViewImageSrc;
            viewImageNode.hidden = false;
        }
        if (viewEmptyNode) {
            viewEmptyNode.hidden = true;
        }
        viewModal.classList.add("open");
        viewModal.setAttribute("aria-hidden", "false");
        document.body.classList.add("account-view-open");
    };

    const clearCroppedData = () => {
        if (!croppedDataField) return;
        croppedDataField.value = "";
    };

    const setCroppedData = (dataValue) => {
        if (!croppedDataField) return;
        croppedDataField.value = String(dataValue || "");
    };

    const formatBytes = (bytesValue) => {
        const bytes = Number(bytesValue);
        if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
        if (bytes < 1024) return `${Math.round(bytes)} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const revokePreviewUrl = () => {
        if (!previewImageUrl) return;
        URL.revokeObjectURL(previewImageUrl);
        previewImageUrl = "";
    };

    const revokeCropUrl = () => {
        if (!cropObjectUrl) return;
        URL.revokeObjectURL(cropObjectUrl);
        cropObjectUrl = "";
    };

    const assignFileToInput = (fileNode) => {
        if (!imageInput || !fileNode) return false;
        if (typeof DataTransfer === "undefined") return false;
        try {
            const transfer = new DataTransfer();
            transfer.items.add(fileNode);
            imageInput.files = transfer.files;
            return true;
        } catch (_) {
            return false;
        }
    };

    const persistCroppedImage = async (croppedDataUrl) => {
        const response = await fetch(imageSaveUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                cropped_data: String(croppedDataUrl || ""),
            }),
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload || payload.ok !== true) {
            const errorMessage = String(payload?.error || "Could not save profile photo.");
            throw new Error(errorMessage);
        }

        const imageUrl = String(payload.image_url || "").trim();
        if (!imageUrl) {
            throw new Error("Profile photo saved but URL is missing.");
        }
        return imageUrl;
    };

    const loadImageNodeFromFile = (fileNode) => {
        return new Promise((resolve, reject) => {
            revokeCropUrl();
            cropObjectUrl = URL.createObjectURL(fileNode);
            const image = new Image();
            image.onload = () => {
                resolve(image);
            };
            image.onerror = () => {
                revokeCropUrl();
                reject(new Error("Image could not be read."));
            };
            image.src = cropObjectUrl;
        });
    };

    const ensureImageNode = () => {
        if (imageNode) return imageNode;
        imageNode = document.createElement("img");
        imageNode.setAttribute("data-account-avatar-image", "");
        imageNode.alt = "Profile image";
        imageNode.hidden = true;
        previewNode.insertBefore(imageNode, previewNode.firstChild);
        return imageNode;
    };

    const showInitial = () => {
        previewNode.classList.remove("has-image");
        const activeImage = ensureImageNode();
        activeImage.hidden = true;
        activeImage.removeAttribute("src");
        if (initialNode) {
            initialNode.hidden = false;
        }
        activeViewImageSrc = "";
        setViewAvailability(false);
        closeViewModal();
        updateQuickButtonLabel(false);
    };

    const showImage = (src) => {
        const cleanSrc = String(src || "").trim();
        if (!cleanSrc) {
            showInitial();
            return;
        }

        const activeImage = ensureImageNode();
        activeImage.src = cleanSrc;
        activeImage.hidden = false;
        previewNode.classList.add("has-image");
        if (initialNode) {
            initialNode.hidden = true;
        }
        activeViewImageSrc = cleanSrc;
        if (viewImageNode) {
            viewImageNode.src = cleanSrc;
        }
        setViewAvailability(true);
        updateQuickButtonLabel(true);
    };

    const applyPreview = (inputNode) => {
        if (!inputNode) return;
        const start = inputNode.getAttribute("data-avatar-start") || "#2388e2";
        const end = inputNode.getAttribute("data-avatar-end") || "#1f6fc9";
        const ring = inputNode.getAttribute("data-avatar-ring") || "#c0d5ee";
        previewNode.style.setProperty("--avatar-start", start);
        previewNode.style.setProperty("--avatar-end", end);
        previewNode.style.setProperty("--avatar-ring", ring);
    };

    const setRemoveToggleEnabled = (isEnabled) => {
        if (!removeToggle) return;
        removeToggle.disabled = !isEnabled;
        if (removeToggleWrap) {
            removeToggleWrap.classList.toggle("is-disabled", !isEnabled);
        }
    };

    const openCropModal = () => {
        if (!cropModal) return;
        closeViewModal();
        cropModal.classList.add("open");
        cropModal.setAttribute("aria-hidden", "false");
        document.body.classList.add("account-crop-open");
    };

    const closeCropModal = () => {
        if (!cropModal) return;
        cropModal.classList.remove("open");
        cropModal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("account-crop-open");
    };

    const clampCropOffsets = () => {
        if (!cropCanvas || !cropState.image) return;
        const renderWidth = cropState.image.width * cropState.scale;
        const renderHeight = cropState.image.height * cropState.scale;

        const minX = Math.min(0, cropCanvas.width - renderWidth);
        const maxX = 0;
        const minY = Math.min(0, cropCanvas.height - renderHeight);
        const maxY = 0;

        cropState.offsetX = Math.min(maxX, Math.max(minX, cropState.offsetX));
        cropState.offsetY = Math.min(maxY, Math.max(minY, cropState.offsetY));
    };

    const drawCropCanvas = () => {
        if (!cropCanvas || !cropCtx || !cropState.image) return;
        cropCtx.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
        cropCtx.fillStyle = "#0f172a";
        cropCtx.fillRect(0, 0, cropCanvas.width, cropCanvas.height);
        cropCtx.imageSmoothingEnabled = true;
        cropCtx.imageSmoothingQuality = "high";
        cropCtx.drawImage(
            cropState.image,
            cropState.offsetX,
            cropState.offsetY,
            cropState.image.width * cropState.scale,
            cropState.image.height * cropState.scale
        );
    };

    const setCropScale = (nextScale, anchorX = null, anchorY = null) => {
        if (!cropCanvas || !cropState.image) return;
        const oldScale = cropState.scale;
        const minScale = cropState.minScale;
        const boundedScale = Math.max(minScale, Math.min(minScale * 3, nextScale));
        if (Math.abs(boundedScale - oldScale) < 0.0001) return;

        const focusX = anchorX === null ? (cropCanvas.width / 2) : anchorX;
        const focusY = anchorY === null ? (cropCanvas.height / 2) : anchorY;
        const imagePointX = (focusX - cropState.offsetX) / oldScale;
        const imagePointY = (focusY - cropState.offsetY) / oldScale;

        cropState.scale = boundedScale;
        cropState.offsetX = focusX - (imagePointX * boundedScale);
        cropState.offsetY = focusY - (imagePointY * boundedScale);
        clampCropOffsets();
        drawCropCanvas();

        if (cropZoom) {
            const percent = Math.round((boundedScale / minScale) * 100);
            cropZoom.value = String(Math.max(100, Math.min(300, percent)));
        }
    };

    const closeCropEditor = ({ resetInput = false } = {}) => {
        closeCropModal();
        cropState.image = null;
        cropState.dragging = false;
        cropState.pointerId = null;
        if (cropCanvas) {
            cropCanvas.classList.remove("dragging");
        }
        revokeCropUrl();
        if (resetInput && imageInput) {
            imageInput.value = "";
        }
    };

    const openCropEditor = async (fileNode) => {
        if (!cropCanvas || !cropCtx) {
            throw new Error("Crop editor is not available.");
        }

        const loadedImage = await loadImageNodeFromFile(fileNode);
        cropState.image = loadedImage;
        cropState.dragging = false;
        cropState.pointerId = null;

        const minScale = Math.max(
            cropCanvas.width / loadedImage.width,
            cropCanvas.height / loadedImage.height
        );
        cropState.minScale = minScale;
        cropState.scale = minScale;
        cropState.offsetX = (cropCanvas.width - (loadedImage.width * minScale)) / 2;
        cropState.offsetY = (cropCanvas.height - (loadedImage.height * minScale)) / 2;
        clampCropOffsets();
        drawCropCanvas();

        if (cropZoom) {
            cropZoom.value = "100";
        }
        openCropModal();
    };

    const canvasToBlob = (canvasNode, mime, quality) => (
        new Promise((resolve) => {
            canvasNode.toBlob((blob) => resolve(blob), mime, quality);
        })
    );

    const blobToDataUrl = (blobNode) => (
        new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error("Could not encode cropped image."));
            reader.readAsDataURL(blobNode);
        })
    );

    const buildCroppedBlob = async () => {
        if (!cropCanvas || !cropState.image) {
            throw new Error("No image available for cropping.");
        }

        const sourceX = Math.max(0, (0 - cropState.offsetX) / cropState.scale);
        const sourceY = Math.max(0, (0 - cropState.offsetY) / cropState.scale);
        const sourceW = Math.min(cropState.image.width, cropCanvas.width / cropState.scale);
        const sourceH = Math.min(cropState.image.height, cropCanvas.height / cropState.scale);
        const targetSize = 1080;

        let workCanvas = document.createElement("canvas");
        workCanvas.width = targetSize;
        workCanvas.height = targetSize;
        let workCtx = workCanvas.getContext("2d", { alpha: false });
        if (!workCtx) {
            throw new Error("Crop rendering failed.");
        }
        workCtx.imageSmoothingEnabled = true;
        workCtx.imageSmoothingQuality = "high";
        workCtx.drawImage(cropState.image, sourceX, sourceY, sourceW, sourceH, 0, 0, targetSize, targetSize);

        const encodeCandidates = async (canvasNode) => {
            const formatPlan = [
                { type: "image/webp", qualities: [0.92, 0.86, 0.78, 0.7, 0.62] },
                { type: "image/jpeg", qualities: [0.9, 0.82, 0.74, 0.66, 0.58] },
                { type: "image/png", qualities: [undefined] },
            ];

            let smallestBlob = null;
            for (const format of formatPlan) {
                for (const quality of format.qualities) {
                    const blob = await canvasToBlob(canvasNode, format.type, quality);
                    if (!blob) continue;
                    if (!smallestBlob || blob.size < smallestBlob.size) {
                        smallestBlob = blob;
                    }
                    if (blob.size <= maxUploadBytes) {
                        return blob;
                    }
                }
            }
            return smallestBlob;
        };

        let bestBlob = null;
        for (let attempt = 0; attempt < 6; attempt += 1) {
            const blob = await encodeCandidates(workCanvas);
            if (blob && (!bestBlob || blob.size < bestBlob.size)) {
                bestBlob = blob;
            }
            if (blob && blob.size <= maxUploadBytes) {
                return blob;
            }

            if (workCanvas.width <= 420) break;
            const nextSize = Math.max(420, Math.round(workCanvas.width * 0.84));
            const resizedCanvas = document.createElement("canvas");
            resizedCanvas.width = nextSize;
            resizedCanvas.height = nextSize;
            const resizedCtx = resizedCanvas.getContext("2d", { alpha: false });
            if (!resizedCtx) break;
            resizedCtx.imageSmoothingEnabled = true;
            resizedCtx.imageSmoothingQuality = "high";
            resizedCtx.drawImage(workCanvas, 0, 0, nextSize, nextSize);
            workCanvas = resizedCanvas;
            workCtx = resizedCtx;
            if (!workCtx) break;
        }

        if (!bestBlob) {
            throw new Error("Could not crop this image.");
        }
        if (bestBlob.size > maxUploadBytes) {
            throw new Error(`Cropped image is too large. Keep it under ${formatBytes(maxUploadBytes)}.`);
        }
        return bestBlob;
    };

    const handleCropApply = async () => {
        if (!cropState.image) return;
        if (cropApplyButton) cropApplyButton.disabled = true;
        setImageStatus("Applying crop...");

        try {
            const croppedBlob = await buildCroppedBlob();
            const extension = croppedBlob.type.includes("webp")
                ? "webp"
                : (croppedBlob.type.includes("png") ? "png" : "jpg");
            const croppedFile = new File(
                [croppedBlob],
                `profile-crop.${extension}`,
                {
                    type: croppedBlob.type || `image/${extension}`,
                    lastModified: Date.now(),
                }
            );

            const dataUrl = await blobToDataUrl(croppedBlob);
            setCroppedData(dataUrl);
            if (!assignFileToInput(croppedFile) && imageInput) {
                imageInput.value = "";
            }

            revokePreviewUrl();
            previewImageUrl = URL.createObjectURL(croppedFile);
            showImage(previewImageUrl);
            setImageName(`${croppedFile.name} (${formatBytes(croppedFile.size)})`);
            setImageStatus("Saving profile photo...");

            const savedImageUrl = await persistCroppedImage(dataUrl);
            const cacheBustedSavedUrl = `${savedImageUrl}${savedImageUrl.includes("?") ? "&" : "?"}v=${Date.now()}`;
            persistedImageSrc = cacheBustedSavedUrl;

            revokePreviewUrl();
            showImage(cacheBustedSavedUrl);
            setImageStatus("Profile photo updated.");
            if (typeof window.showAppToast === "function") {
                window.showRupyToast("Profile photo updated.", "success", 2200);
            }

            if (removeToggle) {
                removeToggle.checked = false;
            }
            setRemoveToggleEnabled(true);
            clearCroppedData();
            if (imageInput) {
                imageInput.value = "";
            }
            closeCropEditor();
        } catch (error) {
            const message = String(error?.message || "Could not apply crop.");
            setImageStatus(message, { error: true });
        } finally {
            if (cropApplyButton) cropApplyButton.disabled = false;
        }
    };

    if (presetInputs.length) {
        presetInputs.forEach((inputNode) => {
            if (inputNode.checked) {
                applyPreview(inputNode);
            }
            inputNode.addEventListener("change", () => {
                if (!inputNode.checked) return;
                applyPreview(inputNode);
            });
        });
    }

    if (cropCanvas && cropCtx) {
        cropCanvas.addEventListener("pointerdown", (event) => {
            if (!cropState.image) return;
            cropState.dragging = true;
            cropState.pointerId = event.pointerId;
            cropState.startX = event.clientX;
            cropState.startY = event.clientY;
            cropCanvas.classList.add("dragging");
            cropCanvas.setPointerCapture(event.pointerId);
        });

        cropCanvas.addEventListener("pointermove", (event) => {
            if (!cropState.dragging || cropState.pointerId !== event.pointerId) return;
            const deltaX = event.clientX - cropState.startX;
            const deltaY = event.clientY - cropState.startY;
            cropState.startX = event.clientX;
            cropState.startY = event.clientY;
            cropState.offsetX += deltaX;
            cropState.offsetY += deltaY;
            clampCropOffsets();
            drawCropCanvas();
        });

        const endDrag = (event) => {
            if (!cropState.dragging) return;
            if (event && cropState.pointerId !== null && event.pointerId !== cropState.pointerId) return;
            cropState.dragging = false;
            if (cropState.pointerId !== null) {
                try {
                    cropCanvas.releasePointerCapture(cropState.pointerId);
                } catch (_) {
                    // Ignore release failures.
                }
            }
            cropState.pointerId = null;
            cropCanvas.classList.remove("dragging");
        };

        cropCanvas.addEventListener("pointerup", endDrag);
        cropCanvas.addEventListener("pointercancel", endDrag);
        cropCanvas.addEventListener("wheel", (event) => {
            if (!cropState.image) return;
            event.preventDefault();
            const step = event.deltaY < 0 ? 0.08 : -0.08;
            setCropScale(cropState.scale * (1 + step), event.offsetX, event.offsetY);
        }, { passive: false });
    }

    if (cropZoom) {
        cropZoom.addEventListener("input", () => {
            if (!cropState.image) return;
            const percent = Number(cropZoom.value || 100);
            const nextScale = cropState.minScale * (percent / 100);
            setCropScale(nextScale);
        });
    }

    if (cropApplyButton) {
        cropApplyButton.addEventListener("click", () => {
            void handleCropApply();
        });
    }

    if (cropCancelButtons.length) {
        cropCancelButtons.forEach((button) => {
            button.addEventListener("click", () => {
                closeCropEditor({ resetInput: true });
                setImageStatus("Image selection canceled.", { error: true });
                setImageName("");
                clearCroppedData();
                if (persistedImageSrc) {
                    showImage(persistedImageSrc);
                } else {
                    showInitial();
                    setRemoveToggleEnabled(false);
                }
            });
        });
    }

    if (cropModal) {
        cropModal.addEventListener("click", (event) => {
            if (event.target !== cropModal) return;
            closeCropEditor({ resetInput: true });
            setImageStatus("Image selection canceled.", { error: true });
            setImageName("");
            clearCroppedData();
            if (persistedImageSrc) {
                showImage(persistedImageSrc);
            } else {
                showInitial();
                setRemoveToggleEnabled(false);
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if (cropModal && cropModal.classList.contains("open")) {
            closeCropEditor({ resetInput: true });
            setImageStatus("Image selection canceled.", { error: true });
            setImageName("");
            clearCroppedData();
            if (persistedImageSrc) {
                showImage(persistedImageSrc);
            } else {
                showInitial();
                setRemoveToggleEnabled(false);
            }
            return;
        }
        if (viewModal && viewModal.classList.contains("open")) {
            closeViewModal();
        }
    });

    if (viewButton) {
        viewButton.addEventListener("click", () => {
            openViewModal();
        });
    }

    previewNode.addEventListener("click", () => {
        if (!activeViewImageSrc) return;
        openViewModal();
    });

    previewNode.addEventListener("keydown", (event) => {
        if (!activeViewImageSrc) return;
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        openViewModal();
    });

    if (viewCloseButtons.length) {
        viewCloseButtons.forEach((button) => {
            button.addEventListener("click", () => {
                closeViewModal();
            });
        });
    }

    if (viewModal) {
        viewModal.addEventListener("click", (event) => {
            if (event.target !== viewModal) return;
            closeViewModal();
        });
    }

    if (imageInput && imagePickers.length) {
        imagePickers.forEach((button) => {
            button.addEventListener("click", () => {
                const targetId = String(button.getAttribute("data-account-image-target") || "").trim();
                if (targetId) {
                    const targetInput = document.getElementById(targetId);
                    if (targetInput) {
                        targetInput.click();
                        return;
                    }
                }
                imageInput.click();
            });
        });
    }

    if (imageInput) {
        imageInput.addEventListener("change", async () => {
            clearCroppedData();
            revokePreviewUrl();
            const selectedFile = imageInput.files && imageInput.files[0];
            if (!selectedFile) {
                setImageStatus("", { hidden: true });
                setImageName("");
                if (removeToggle && removeToggle.checked) {
                    showInitial();
                    return;
                }
                if (persistedImageSrc) {
                    showImage(persistedImageSrc);
                } else {
                    showInitial();
                }
                return;
            }

            try {
                const selectedName = String(selectedFile.name || "profile-image");
                if (!selectedName.includes(".")) {
                    throw new Error("Please choose a valid image file.");
                }
                const extension = selectedName.split(".").pop();
                const allowedExtensions = new Set(["png", "jpg", "jpeg", "jfif", "webp", "gif", "avif"]);
                if (!allowedExtensions.has(String(extension || "").toLowerCase())) {
                    throw new Error("Supported formats: PNG, JPG, JPEG, JFIF, WEBP, GIF, AVIF.");
                }
                if (selectedFile.size > maxUploadBytes) {
                    throw new Error(`Image is too large. Keep it under ${formatBytes(maxUploadBytes)}.`);
                }

                setImageName(selectedName);
                setImageStatus("Opening crop editor...");
                await openCropEditor(selectedFile);
            } catch (error) {
                if (imageInput) {
                    imageInput.value = "";
                }
                const message = String(error?.message || "Could not process image.");
                setImageStatus(message, { error: true });
                setImageName("");
                if (persistedImageSrc) {
                    showImage(persistedImageSrc);
                } else {
                    showInitial();
                }
            }
        });
    }

    if (removeToggle) {
        removeToggle.addEventListener("change", () => {
            if (removeToggle.checked) {
                if (imageInput) {
                    imageInput.value = "";
                }
                setImageStatus("", { hidden: true });
                setImageName("");
                clearCroppedData();
                revokePreviewUrl();
                showInitial();
                return;
            }

            const selectedFile = imageInput && imageInput.files ? imageInput.files[0] : null;
            if (selectedFile) {
                if (previewImageUrl) {
                    showImage(previewImageUrl);
                }
                return;
            }

            if (persistedImageSrc) {
                setImageStatus("", { hidden: true });
                setImageName("");
                showImage(persistedImageSrc);
                return;
            }
            showInitial();
        });
    }

    if (persistedImageSrc) {
        showImage(persistedImageSrc);
        setRemoveToggleEnabled(true);
    } else {
        setRemoveToggleEnabled(false);
    }
    setImageStatus("", { hidden: true });
    setImageName("");
    clearCroppedData();

    window.addEventListener("beforeunload", () => {
        revokePreviewUrl();
        revokeCropUrl();
    });
}

function setupSidebarToggle() {
    const sidebar = document.querySelector(".sidebar");
    const toggleButtons = document.querySelectorAll("[data-sidebar-toggle]");
    if (!sidebar || !toggleButtons.length) return;

    const mediaQuery = window.matchMedia("(max-width: 768px)");
    let hasLocalOverride = false;

    const applyCollapsedState = (isCollapsed) => {
        sidebar.classList.toggle("collapsed", isCollapsed);
    };

    const syncFromServer = async ({ force = false } = {}) => {
        if (mediaQuery.matches) {
            applyCollapsedState(false);
            return;
        }

        try {
            const response = await fetch("/ui/preferences/sidebar", {
                method: "GET",
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                throw new Error("Failed to load sidebar preference");
            }
            const data = await response.json();
            if (force || !hasLocalOverride) {
                applyCollapsedState(Boolean(data.sidebar_collapsed));
            }
        } catch (_) {
            if (force || !hasLocalOverride) {
                applyCollapsedState(false);
            }
        }
    };

    const persistPreference = async (isCollapsed) => {
        try {
            await fetch("/ui/preferences/sidebar", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({ collapsed: isCollapsed }),
            });
        } catch (_) {
            // Keep UI state even when persistence fails.
        }
    };

    void syncFromServer({ force: true });
    mediaQuery.addEventListener("change", () => {
        hasLocalOverride = false;
        if (mediaQuery.matches) {
            applyCollapsedState(false);
            return;
        }
        void syncFromServer({ force: true });
    });

    toggleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const shouldCollapse = !sidebar.classList.contains("collapsed");
            hasLocalOverride = true;
            applyCollapsedState(shouldCollapse);
            if (!mediaQuery.matches) {
                void persistPreference(shouldCollapse);
            }
        });
    });
}

function setupSidebarBrandCoinSpin() {
    const brandLink = document.querySelector(".sidebar-brand");
    const coin = brandLink ? brandLink.querySelector(".brand-coin") : null;
    if (!brandLink || !coin) return;

    const spinMs = prefersReducedMotion() ? 0 : 760;

    const triggerSpin = () => {
        coin.classList.remove("is-click-spin");
        if (spinMs <= 0) return;
        // Force reflow so animation can restart on every click.
        void coin.offsetWidth;
        coin.classList.add("is-click-spin");
        window.setTimeout(() => {
            coin.classList.remove("is-click-spin");
        }, spinMs + 30);
    };

    coin.addEventListener("click", (event) => {
        triggerSpin();

        const href = brandLink.getAttribute("href") || "";
        const isModifiedClick = event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
        if (isModifiedClick || spinMs <= 0 || !href) return;

        let targetPath = "";
        try {
            targetPath = new URL(href, window.location.origin).pathname;
        } catch (_) {
            return;
        }

        if (targetPath === window.location.pathname) {
            event.preventDefault();
            return;
        }

        event.preventDefault();
        window.setTimeout(() => {
            window.location.assign(href);
        }, Math.min(spinMs - 180, 540));
    });
}

function setupPasswordToggles() {
    const toggles = document.querySelectorAll("[data-password-toggle]");
    if (!toggles.length) return;

    toggles.forEach((toggle) => {
        const targetId = toggle.getAttribute("data-target");
        const targetInput = targetId ? document.getElementById(targetId) : null;
        if (!targetInput) return;

        toggle.addEventListener("click", () => {
            const isPassword = targetInput.type === "password";
            targetInput.type = isPassword ? "text" : "password";

            const icon = toggle.querySelector("i");
            if (icon) {
                icon.classList.toggle("fa-eye", !isPassword);
                icon.classList.toggle("fa-eye-slash", isPassword);
            }

            toggle.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
        });
    });
}

function setupLogoutConfirmation() {
    const modal = document.querySelector("[data-logout-modal]");
    const logoutForms = document.querySelectorAll("form[data-logout-form]");
    if (!modal || !logoutForms.length) return;

    const confirmBtn = modal.querySelector("[data-logout-confirm]");
    const cancelBtn = modal.querySelector("[data-logout-cancel]");
    let pendingForm = null;

    const closeModal = () => {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
        pendingForm = null;
    };

    const openModal = (form) => {
        pendingForm = form;
        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        if (cancelBtn) cancelBtn.focus();
    };

    logoutForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            openModal(form);
        });
    });

    if (confirmBtn) {
        confirmBtn.addEventListener("click", () => {
            if (!pendingForm) {
                closeModal();
                return;
            }
            const formToSubmit = pendingForm;
            closeModal();
            formToSubmit.submit();
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener("click", closeModal);
    }

    modal.addEventListener("click", (event) => {
        if (event.target === modal) closeModal();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal.classList.contains("open")) {
            closeModal();
        }
    });
}

function setupActionConfirmModal() {
    const modal = document.querySelector("[data-action-modal]");
    const forms = Array.from(document.querySelectorAll("form[data-confirm-form]"));
    if (!modal || !forms.length) return;

    const titleNode = modal.querySelector("[data-action-title]");
    const messageNode = modal.querySelector("[data-action-message]");
    const cancelButton = modal.querySelector("[data-action-cancel]");
    const confirmButton = modal.querySelector("[data-action-confirm]");
    const defaultConfirmLabel = confirmButton ? String(confirmButton.textContent || "").trim() : "Continue";
    let pendingForm = null;

    const closeModal = () => {
        modal.classList.remove("open");
        modal.classList.remove("is-danger");
        modal.setAttribute("aria-hidden", "true");
        if (confirmButton) {
            confirmButton.textContent = defaultConfirmLabel;
            confirmButton.classList.remove("is-danger");
        }
        pendingForm = null;
    };

    const openModal = (form) => {
        pendingForm = form;

        const title = String(form.getAttribute("data-confirm-title") || "Confirm Action").trim();
        const message = String(form.getAttribute("data-confirm-message") || "Are you sure you want to continue?").trim();
        const variant = String(form.getAttribute("data-confirm-variant") || "").trim().toLowerCase();
        const ctaLabel = String(form.getAttribute("data-confirm-cta") || "").trim();
        const iconClassRaw = String(form.getAttribute("data-confirm-icon") || "").trim();
        const safeIconClass = /^[a-z0-9\-\s]+$/i.test(iconClassRaw) ? iconClassRaw : "";
        const iconClass = safeIconClass || (variant === "danger" ? "fa-solid fa-trash-can" : "fa-solid fa-triangle-exclamation");
        const isDanger = variant === "danger";

        if (titleNode) {
            titleNode.innerHTML = `
                <i class="${escapeHtml(iconClass)}"></i>
                ${escapeHtml(title)}
            `;
        }
        if (messageNode) {
            messageNode.textContent = message;
        }
        if (confirmButton) {
            confirmButton.textContent = ctaLabel || (isDanger ? "Delete" : defaultConfirmLabel);
            confirmButton.classList.toggle("is-danger", isDanger);
        }
        modal.classList.toggle("is-danger", isDanger);

        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        if (cancelButton) cancelButton.focus();
    };

    forms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (form.dataset.confirmed === "true") {
                form.dataset.confirmed = "false";
                return;
            }
            event.preventDefault();
            openModal(form);
        });
    });

    if (confirmButton) {
        confirmButton.addEventListener("click", () => {
            if (!pendingForm) {
                closeModal();
                return;
            }

            const formToSubmit = pendingForm;
            closeModal();
            formToSubmit.dataset.confirmed = "true";
            formToSubmit.requestSubmit();
        });
    }

    if (cancelButton) {
        cancelButton.addEventListener("click", closeModal);
    }

    modal.addEventListener("click", (event) => {
        if (event.target === modal) closeModal();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal.classList.contains("open")) {
            closeModal();
        }
    });
}

function setupNotificationDrawer(drawer, bellButton) {
    if (!drawer) return;

    const items = Array.from(drawer.querySelectorAll("[data-notif-item]"));
    const tabButtons = Array.from(drawer.querySelectorAll("[data-notif-tab]"));
    const emptyState = drawer.querySelector("[data-notif-empty]");
    const markAllReadButton = drawer.querySelector("[data-mark-all-read]");
    const badgeTargets = document.querySelectorAll("[data-notification-count]");
    const unreadTargets = drawer.querySelectorAll("[data-notification-unread]");
    let activeTab = "all";
    let isMarkAllPending = false;

    const isRead = (item) => item.classList.contains("is-read");

    const setReadState = (item, shouldRead) => {
        item.classList.toggle("is-read", shouldRead);
        item.classList.toggle("is-unread", !shouldRead);
        const markButton = item.querySelector("[data-mark-read]");
        if (markButton) {
            markButton.hidden = shouldRead;
        }
    };

    const unreadCount = () => {
        let count = 0;
        items.forEach((item) => {
            if (!isRead(item)) count += 1;
        });
        return count;
    };

    const refreshBadges = () => {
        const count = unreadCount();
        const label = count > 99 ? "99+" : String(count);

        badgeTargets.forEach((target) => {
            if (count > 0) {
                target.hidden = false;
                target.textContent = label;
            } else {
                target.hidden = true;
            }
        });

        unreadTargets.forEach((target) => {
            target.textContent = String(count);
        });

        if (bellButton) {
            bellButton.classList.toggle("has-unread", count > 0);
        }

        if (markAllReadButton) {
            markAllReadButton.disabled = count === 0 || isMarkAllPending;
        }
    };

    const refreshTabFilter = () => {
        let visibleCount = 0;
        items.forEach((item) => {
            const group = String(item.getAttribute("data-group") || "");
            const shouldShow = activeTab === "all" || group === activeTab;
            item.hidden = !shouldShow;
            if (shouldShow) visibleCount += 1;
        });

        tabButtons.forEach((button) => {
            button.classList.toggle("active", button.getAttribute("data-notif-tab") === activeTab);
        });

        if (emptyState) {
            emptyState.hidden = visibleCount !== 0;
        }
    };

    const refresh = () => {
        refreshTabFilter();
        refreshBadges();
    };

    const postMarkRead = async (notificationId, useKeepAlive = false) => {
        // VIVA: FRONTEND API - mark one notification as read in the backend.
        const response = await fetch(`/notifications/read/${encodeURIComponent(notificationId)}`, {
            method: "POST",
            headers: { Accept: "application/json" },
            keepalive: useKeepAlive,
        });
        if (!response.ok) {
            throw new Error("Failed to mark notification as read");
        }
    };

    tabButtons.forEach((button) => {
        button.addEventListener("click", () => {
            activeTab = button.getAttribute("data-notif-tab") || "all";
            refresh();
        });
    });

    items.forEach((item) => {
        const markButton = item.querySelector("[data-mark-read]");
        if (markButton) {
            markButton.addEventListener("click", async (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (isRead(item)) return;

                const notificationId = String(item.getAttribute("data-id") || "");
                if (!notificationId) return;

                markButton.disabled = true;
                setReadState(item, true);
                refresh();

                try {
                    await postMarkRead(notificationId);
                } catch (_) {
                    markButton.disabled = false;
                    setReadState(item, false);
                    refresh();
                    showRupyToast("Could not update notification. Try again.", "error");
                }
            });
        }

        const link = item.querySelector("[data-notif-link]");
        if (link) {
            link.addEventListener("click", () => {
                if (isRead(item)) return;
                const notificationId = String(item.getAttribute("data-id") || "");
                if (!notificationId) return;

                setReadState(item, true);
                refresh();
                void postMarkRead(notificationId, true).catch(() => {
                    // Ignore failures on navigation-triggered reads.
                });
            });
        }
    });

    if (markAllReadButton) {
        markAllReadButton.addEventListener("click", async () => {
            if (isMarkAllPending) return;
            const unreadItems = items.filter((item) => !isRead(item));
            if (!unreadItems.length) {
                refresh();
                return;
            }

            const unreadIds = unreadItems
                .map((item) => String(item.getAttribute("data-id") || ""))
                .filter(Boolean);
            if (!unreadIds.length) return;

            const previousState = unreadItems.map((item) => ({
                item,
                read: isRead(item),
            }));

            isMarkAllPending = true;
            items.forEach((item) => {
                if (!isRead(item)) setReadState(item, true);
            });
            refresh();

            try {
                // VIVA: FRONTEND API - bulk mark unread notifications as read.
                const response = await fetch("/notifications/read-all", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    body: JSON.stringify({ ids: unreadIds }),
                });
                if (!response.ok) {
                    throw new Error("Failed to mark all as read");
                }
                const data = await response.json().catch(() => ({}));
                if (Number(data.updated || 0) > 0) {
                    showRupyToast(data.message || "All notifications marked as read.", "info");
                }
            } catch (_) {
                previousState.forEach(({ item, read }) => {
                    setReadState(item, read);
                });
                showRupyToast("Could not mark all notifications. Try again.", "error");
            } finally {
                isMarkAllPending = false;
                refresh();
            }
        });
    }

    drawer.addEventListener("drawer:open", refresh);
    refresh();
}

function setupSearchDrawer(drawer) {
    if (!drawer) return;

    const input = drawer.querySelector("[data-search-input]");
    const resultsContainer = drawer.querySelector("[data-search-results]");
    const emptyState = drawer.querySelector("[data-search-empty]");
    const loadingState = drawer.querySelector("[data-search-loading]");
    const summaryState = drawer.querySelector("[data-search-summary]");
    const loadMoreButton = drawer.querySelector("[data-search-load-more]");
    const resultsTitle = drawer.querySelector("[data-search-results-title]");
    const recentContainer = drawer.querySelector("[data-recent-searches]");
    const queryChips = drawer.querySelectorAll("[data-search-query]");
    if (!input || !resultsContainer) return;

    const storageKey = "expensepro-recent-searches";
    let recentSearches = (() => {
        try {
            const rawValue = localStorage.getItem(storageKey);
            const parsed = rawValue ? JSON.parse(rawValue) : [];
            return Array.isArray(parsed) ? parsed.filter(Boolean).slice(0, 6) : [];
        } catch (_) {
            return [];
        }
    })();

    const saveRecentSearches = () => {
        localStorage.setItem(storageKey, JSON.stringify(recentSearches));
    };

    const trackSearch = (query) => {
        const cleanValue = String(query || "").trim();
        if (!cleanValue) return;

        recentSearches = [
            cleanValue,
            ...recentSearches.filter((item) => item.toLowerCase() !== cleanValue.toLowerCase()),
        ].slice(0, 6);

        saveRecentSearches();
        renderRecentSearches();
    };

    const renderRecentSearches = () => {
        if (!recentContainer) return;
        recentContainer.innerHTML = "";

        if (!recentSearches.length) {
            const placeholder = document.createElement("span");
            placeholder.className = "drawer-empty-inline";
            placeholder.textContent = "No recent searches yet";
            recentContainer.appendChild(placeholder);
            return;
        }

        recentSearches.forEach((query) => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = "recent-search-chip";
            chip.textContent = query;
            chip.addEventListener("click", () => {
                input.value = query;
                void updateResults(true);
                input.focus();
            });
            recentContainer.appendChild(chip);
        });
    };

    const hasActiveQuery = () => {
        return Boolean(String(input.value || "").trim());
    };

    const buildSearchParams = () => {
        const params = new URLSearchParams();
        const q = String(input.value || "").trim();

        if (q) params.set("q", q);
        params.set("limit", "18");
        return params;
    };

    const setLoading = (isLoading) => {
        if (loadingState) loadingState.hidden = !isLoading;
        resultsContainer.classList.toggle("is-loading", Boolean(isLoading));
        if (loadMoreButton) loadMoreButton.disabled = Boolean(isLoading);
    };

    let activeController = null;
    let debounceHandle = null;
    let requestCounter = 0;
    let lastRenderedResults = [];
    let currentPage = 1;
    let hasMoreResults = false;
    let totalResultCount = 0;
    let activeFilterKey = "";

    const renderSummary = () => {
        if (!summaryState) return;

        if (!totalResultCount && !hasActiveQuery()) {
            summaryState.hidden = true;
            summaryState.textContent = "";
            return;
        }

        const showingCount = lastRenderedResults.length;
        const queryLabel = hasActiveQuery() ? "search" : "recent";
        summaryState.textContent = `Showing ${showingCount} of ${totalResultCount} ${queryLabel} transactions`;
        summaryState.hidden = false;
    };

    const updateLoadMoreVisibility = () => {
        if (!loadMoreButton) return;
        loadMoreButton.hidden = !(hasMoreResults && lastRenderedResults.length > 0);
    };

    const fetchResults = async (page, appendResults = false) => {
        const params = buildSearchParams();
        const filterKey = params.toString();
        params.set("page", String(page));
        if (activeController) {
            activeController.abort();
        }

        requestCounter += 1;
        const requestId = requestCounter;
        activeController = new AbortController();
        setLoading(true);

        try {
            // VIVA: FRONTEND API - request filtered expense search results from Flask.
            const response = await fetch(`/api/search/expenses?${params.toString()}`, {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                signal: activeController.signal,
            });

            if (!response.ok) {
                throw new Error("Search failed");
            }

            const payload = await response.json().catch(() => ({}));
            if (requestId !== requestCounter) return;

            const resultItems = Array.isArray(payload.results) ? payload.results : [];
            const pagination = payload && payload.pagination ? payload.pagination : {};
            const pageFromApi = Number(pagination.page || page || 1);
            const totalFromApi = Number(payload.total_count || resultItems.length || 0);
            const hasMoreFromApi = Boolean(pagination.has_more);

            currentPage = pageFromApi;
            totalResultCount = totalFromApi;
            hasMoreResults = hasMoreFromApi;
            activeFilterKey = filterKey;

            if (appendResults) {
                renderResults([...lastRenderedResults, ...resultItems]);
            } else {
                renderResults(resultItems);
            }

            renderSummary();
            updateLoadMoreVisibility();
        } catch (error) {
            if (error && error.name === "AbortError") {
                return;
            }
            throw error;
        } finally {
            if (requestId === requestCounter) {
                setLoading(false);
            }
        }
    };

    const renderResults = (resultItems) => {
        resultsContainer.innerHTML = "";
        lastRenderedResults = Array.isArray(resultItems) ? resultItems : [];

        lastRenderedResults.forEach((item) => {
            const resultNode = document.createElement("a");
            resultNode.className = "search-result-item";
            resultNode.href = String(item.url || "/expenses");
            resultNode.innerHTML = `
                <div class="search-result-main">
                    <p class="search-result-title">${escapeHtml(item.title || "Transaction")}</p>
                    <p class="search-result-meta">${escapeHtml(item.category || "Uncategorized")} | ${escapeHtml(item.date || "-")}</p>
                </div>
                <p class="search-result-amount">-${escapeHtml(item.amount_display || "\u20B90.00")}</p>
            `;
            resultNode.addEventListener("click", () => {
                trackSearch(input.value || item.title || item.category || "");
            });
            resultsContainer.appendChild(resultNode);
        });

        if (emptyState) {
            emptyState.hidden = lastRenderedResults.length !== 0;
        }
    };

    const updateResults = async (forceRefresh = false) => {
        const paramsForKey = buildSearchParams();
        const filterKey = paramsForKey.toString();
        const shouldShowSearchTitle = hasActiveQuery();
        if (resultsTitle) {
            resultsTitle.textContent = shouldShowSearchTitle ? "Search Results" : "Recent transactions";
        }

        if (!forceRefresh && filterKey === activeFilterKey && currentPage === 1) {
            renderSummary();
            updateLoadMoreVisibility();
            return;
        }

        currentPage = 1;
        hasMoreResults = false;
        totalResultCount = 0;

        try {
            await fetchResults(1, false);
            if (emptyState) {
                emptyState.textContent = "No matching transactions found.";
            }
            if (resultsTitle && shouldShowSearchTitle) {
                resultsTitle.textContent = `Search Results (${totalResultCount})`;
            }
        } catch (_) {
            resultsContainer.innerHTML = "";
            lastRenderedResults = [];
            hasMoreResults = false;
            totalResultCount = 0;
            if (emptyState) {
                emptyState.hidden = false;
                emptyState.textContent = "Search failed. Please retry.";
            }
            if (summaryState) {
                summaryState.hidden = true;
                summaryState.textContent = "";
            }
            updateLoadMoreVisibility();
            if (resultsTitle) {
                resultsTitle.textContent = "Search Results";
            }
        }
    };

    const scheduleResultsUpdate = () => {
        if (debounceHandle) {
            window.clearTimeout(debounceHandle);
        }
        debounceHandle = window.setTimeout(() => {
            void updateResults();
        }, 220);
    };

    const loadMoreResults = async () => {
        if (!hasMoreResults) return;
        const nextPage = currentPage + 1;
        try {
            await fetchResults(nextPage, true);
            if (resultsTitle && hasActiveQuery()) {
                resultsTitle.textContent = `Search Results (${totalResultCount})`;
            }
        } catch (_) {
            showRupyToast("Could not load more results right now.", "error");
        }
    };

    input.addEventListener("input", scheduleResultsUpdate);
    input.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        const query = input.value.trim();
        trackSearch(query);
        await updateResults(true);
        const firstResult = resultsContainer.querySelector(".search-result-item");
        if (firstResult) {
            window.location.href = firstResult.href;
        }
    });

    if (loadMoreButton) {
        loadMoreButton.addEventListener("click", () => {
            void loadMoreResults();
        });
    }

    queryChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-search-query") || "";
            input.value = query;
            activeFilterKey = "";
            void updateResults(true);
            input.focus();
            trackSearch(query);
        });
    });

    drawer.addEventListener("drawer:open", () => {
        renderRecentSearches();
        activeFilterKey = "";
        void updateResults(true);
        window.setTimeout(() => input.focus(), 120);
    });

    renderRecentSearches();
    void updateResults(true);
}

function setupCategorySelects() {
    const selects = Array.from(document.querySelectorAll("[data-category-select]"));
    if (!selects.length) return;

    const setHostCardOpenState = (root, isOpen) => {
        const hostCard = root.closest(".card");
        if (!hostCard) return;
        hostCard.classList.toggle("category-select-host-open", Boolean(isOpen));
    };

    const closeSelect = (root) => {
        const trigger = root.querySelector("[data-category-trigger]");
        root.classList.remove("open");
        if (trigger) trigger.setAttribute("aria-expanded", "false");
        setHostCardOpenState(root, false);
    };

    const closeAllSelects = () => {
        selects.forEach((root) => closeSelect(root));
    };

    selects.forEach((root) => {
        const trigger = root.querySelector("[data-category-trigger]");
        const menu = root.querySelector("[data-category-menu]");
        const hiddenInput = root.querySelector("[data-category-input]");
        const currentIcon = root.querySelector("[data-category-current-icon]");
        const currentLabel = root.querySelector("[data-category-current-label]");
        const options = Array.from(root.querySelectorAll("[data-category-option]"));

        if (!trigger || !menu || !hiddenInput || !currentIcon || !currentLabel || !options.length) return;

        const addCategoryEnabled = root.getAttribute("data-add-category") === "true";
        const addFormId = root.getAttribute("data-add-form-id");
        const addInputId = root.getAttribute("data-add-input-id");
        const addForm = addFormId ? document.getElementById(addFormId) : null;
        const addInput = addInputId ? document.getElementById(addInputId) : null;
        const deleteFormId = root.getAttribute("data-delete-form-id");
        const deleteForm = deleteFormId ? document.getElementById(deleteFormId) : null;

        const applySelection = (selectedOption) => {
            const value = String(selectedOption.getAttribute("data-value") || "").trim();
            const iconClass = selectedOption.getAttribute("data-icon") || "fa-solid fa-shapes";
            const iconColor = selectedOption.getAttribute("data-color") || "#7a93ad";
            const labelNode = selectedOption.querySelector(".category-option-label");
            const labelText = labelNode ? labelNode.textContent.trim() : value;

            options.forEach((option) => {
                const isSelected = option === selectedOption;
                option.classList.toggle("is-selected", isSelected);
                option.setAttribute("aria-selected", isSelected ? "true" : "false");
            });

            hiddenInput.value = value;
            currentLabel.textContent = labelText;
            currentIcon.style.setProperty("--category-color", iconColor);

            const icon = document.createElement("i");
            icon.className = iconClass;
            currentIcon.replaceChildren(icon);
        };

        const initialOption = options.find((option) => (
            String(option.getAttribute("data-value") || "") === String(hiddenInput.value || "")
        )) || options.find((option) => (
            String(option.getAttribute("data-value") || "") !== "__add_category__"
        ));

        if (initialOption) {
            applySelection(initialOption);
        }

        const selectedOption = () => (
            options.find((option) => option.classList.contains("is-selected"))
            || options.find((option) => String(option.getAttribute("data-value") || "") !== "__add_category__")
            || options[0]
        );

        const focusOptionByIndex = (targetIndex) => {
            if (!options.length) return null;
            const total = options.length;
            const normalizedIndex = ((targetIndex % total) + total) % total;
            const optionNode = options[normalizedIndex];
            if (!optionNode) return null;

            optionNode.focus({ preventScroll: true });
            optionNode.scrollIntoView({ block: "nearest" });
            return optionNode;
        };

        const openSelect = () => {
            if (root.classList.contains("open")) return;
            closeAllSelects();
            root.classList.add("open");
            trigger.setAttribute("aria-expanded", "true");
            setHostCardOpenState(root, true);
        };

        const closeSelectAndFocusTrigger = () => {
            closeSelect(root);
            trigger.focus({ preventScroll: true });
        };

        const moveOptionFocus = (step) => {
            if (!root.classList.contains("open")) {
                openSelect();
            }
            const currentIndex = options.indexOf(document.activeElement);
            const baseIndex = currentIndex >= 0 ? currentIndex : options.indexOf(selectedOption());
            const fallbackBase = baseIndex >= 0 ? baseIndex : 0;
            focusOptionByIndex(fallbackBase + step);
        };

        trigger.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();

            if (root.classList.contains("open")) {
                closeSelect(root);
                return;
            }
            openSelect();
        });

        trigger.addEventListener("keydown", (event) => {
            const key = String(event.key || "");
            if (key === "ArrowDown") {
                event.preventDefault();
                openSelect();
                const index = options.indexOf(selectedOption());
                focusOptionByIndex(index >= 0 ? index : 0);
                return;
            }
            if (key === "ArrowUp") {
                event.preventDefault();
                openSelect();
                const index = options.indexOf(selectedOption());
                const fallbackIndex = index >= 0 ? index : (options.length - 1);
                focusOptionByIndex(fallbackIndex);
                return;
            }
            if (key === "Enter" || key === " ") {
                event.preventDefault();
                if (root.classList.contains("open")) {
                    closeSelect(root);
                    return;
                }
                openSelect();
                const index = options.indexOf(selectedOption());
                focusOptionByIndex(index >= 0 ? index : 0);
                return;
            }
            if (key === "Escape" && root.classList.contains("open")) {
                event.preventDefault();
                closeSelect(root);
            }
        });

        menu.addEventListener("click", (event) => {
            const deleteTrigger = event.target.closest("[data-category-delete-trigger]");
            if (deleteTrigger && menu.contains(deleteTrigger)) {
                event.preventDefault();
                event.stopPropagation();

                if (!deleteForm) return;

                const categoryId = String(deleteTrigger.getAttribute("data-category-delete-id") || "").trim();
                const categoryName = String(deleteTrigger.getAttribute("data-category-name") || "").trim();
                const protectedCategory = categoryName.toLowerCase() === "other" || categoryName.toLowerCase() === "general";

                if (!categoryId) return;
                if (protectedCategory) {
                    showRupyToast("Default category cannot be deleted.", "info");
                    return;
                }

                deleteForm.action = `/settings/categories/delete/${encodeURIComponent(categoryId)}`;
                deleteForm.setAttribute("data-confirm-title", `Delete ${categoryName}?`);
                deleteForm.setAttribute(
                    "data-confirm-message",
                    `This will permanently remove "${categoryName}" and move existing expense records to Other.`,
                );
                deleteForm.setAttribute("data-confirm-variant", "danger");
                deleteForm.setAttribute("data-confirm-icon", "fa-solid fa-trash-can");
                deleteForm.setAttribute("data-confirm-cta", "Delete Category");
                closeSelect(root);
                deleteForm.requestSubmit();
                return;
            }

            const target = event.target.closest("[data-category-option]");
            if (!target || !menu.contains(target)) return;

            const value = String(target.getAttribute("data-value") || "");
            if (addCategoryEnabled && value === "__add_category__") {
                closeSelect(root);
                const newCategory = window.prompt("Enter new category name:");
                if (!newCategory || !newCategory.trim()) return;

                if (addForm && addInput) {
                    addInput.value = newCategory.trim();
                    addForm.submit();
                }
                return;
            }

            applySelection(target);
            closeSelect(root);
        });

        menu.addEventListener("keydown", (event) => {
            const focusedOption = event.target.closest("[data-category-option]");
            if (!focusedOption || !menu.contains(focusedOption)) return;

            const key = String(event.key || "");
            if (key === "ArrowDown") {
                event.preventDefault();
                moveOptionFocus(1);
                return;
            }
            if (key === "ArrowUp") {
                event.preventDefault();
                moveOptionFocus(-1);
                return;
            }
            if (key === "Home") {
                event.preventDefault();
                focusOptionByIndex(0);
                return;
            }
            if (key === "End") {
                event.preventDefault();
                focusOptionByIndex(options.length - 1);
                return;
            }
            if (key === "Enter" || key === " ") {
                event.preventDefault();
                focusedOption.click();
                return;
            }
            if (key === "Escape") {
                event.preventDefault();
                closeSelectAndFocusTrigger();
            }
        });
    });

    document.addEventListener("click", (event) => {
        const clickedInside = selects.some((root) => root.contains(event.target));
        if (!clickedInside) closeAllSelects();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeAllSelects();
    });
}

function animateInrCounter(node, durationMs = 420) {
    if (!node || node.dataset.counterDone === "true") return;
    if (prefersReducedMotion()) {
        node.dataset.counterDone = "true";
        return;
    }

    const sourceText = String(node.textContent || "").trim();
    const numberMatch = sourceText.match(/-?[\d,]+(?:\.\d+)?/);
    if (!numberMatch || typeof numberMatch.index !== "number") return;

    const parsedTarget = Number(numberMatch[0].replaceAll(",", ""));
    if (!Number.isFinite(parsedTarget)) return;

    node.dataset.counterDone = "true";

    const prefix = sourceText.slice(0, numberMatch.index);
    const suffix = sourceText.slice(numberMatch.index + numberMatch[0].length);
    const isNegative = parsedTarget < 0;
    const targetAbs = Math.abs(parsedTarget);
    const formatter = new Intl.NumberFormat("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });

    const start = performance.now();
    const render = (value) => {
        const safeValue = Math.max(0, value);
        const sign = isNegative ? "-" : "";
        node.textContent = `${prefix}${sign}${formatter.format(safeValue)}${suffix}`;
    };

    const tick = (now) => {
        const elapsed = now - start;
        const progress = Math.min(1, elapsed / durationMs);
        const eased = 1 - Math.pow(1 - progress, 3);
        render(targetAbs * eased);
        if (progress < 1) {
            window.requestAnimationFrame(tick);
        }
    };

    render(0);
    window.requestAnimationFrame(tick);
}

function setupDashboardIntro() {
    const dashboardRoot = document.querySelector("[data-dashboard-page]");
    if (!dashboardRoot) return;

    const header = dashboardRoot.querySelector(".dashboard-header");
    const statCards = Array.from(dashboardRoot.querySelectorAll(".stats-grid .stat-card"));
    const statValues = statCards
        .map((card) => card.querySelector("p"))
        .filter(Boolean);

    if (prefersReducedMotion()) {
        return;
    }

    dashboardRoot.classList.add("is-animating");

    window.requestAnimationFrame(() => {
        if (header) {
            header.classList.add("is-visible");
        }
    });

    statCards.forEach((card, index) => {
        const delayMs = 80 + (index * 80);
        window.setTimeout(() => {
            card.classList.add("is-visible");
        }, delayMs);
    });

    window.setTimeout(() => {
        statValues.forEach((valueNode) => animateInrCounter(valueNode, 420));
    }, 160);
}

function setupHistoryFilterTransitions() {
    const forms = Array.from(document.querySelectorAll("form[data-month-filter]"));
    if (!forms.length) return;

    const submitWithTransition = (form) => {
        if (form.dataset.pendingSubmit === "true") return;
        form.dataset.pendingSubmit = "true";

        if (prefersReducedMotion()) {
            form.submit();
            return;
        }

        const targetSelector = String(form.getAttribute("data-filter-target") || "").trim();
        const transitionTargets = targetSelector
            ? Array.from(document.querySelectorAll(targetSelector))
            : [document.body];

        if (!transitionTargets.length) {
            transitionTargets.push(document.body);
        }

        transitionTargets.forEach((target) => {
            target.classList.add("records-switching");
        });

        window.setTimeout(() => {
            form.submit();
        }, 180);
    };

    forms.forEach((form) => {
        const selects = Array.from(form.querySelectorAll("select"));
        selects.forEach((select) => {
            select.addEventListener("change", () => {
                submitWithTransition(form);
            });
        });
    });
}

function setupDashboardDrawers() {
    const overlay = document.querySelector("[data-dashboard-overlay]");
    const notificationDrawer = document.querySelector("[data-notification-drawer]");
    const searchDrawer = document.querySelector("[data-search-drawer]");
    const notificationToggle = document.querySelector("[data-notification-toggle]");
    const searchToggle = document.querySelector("[data-search-toggle]");
    const closeButtons = document.querySelectorAll("[data-drawer-close]");

    if (!notificationDrawer && !searchDrawer) return;

    setupNotificationDrawer(notificationDrawer, notificationToggle);
    setupSearchDrawer(searchDrawer);

    const reducedMotion = prefersReducedMotion();
    const drawerTransitionMs = reducedMotion ? 1 : 220;
    let activeDrawer = null;
    let hideOverlayTimer = null;

    const showOverlay = () => {
        if (!overlay) return;
        if (hideOverlayTimer) {
            window.clearTimeout(hideOverlayTimer);
            hideOverlayTimer = null;
        }
        overlay.hidden = false;
        window.requestAnimationFrame(() => {
            overlay.classList.add("open");
        });
    };

    const hideOverlay = () => {
        if (!overlay) return;
        overlay.classList.remove("open");
        hideOverlayTimer = window.setTimeout(() => {
            overlay.hidden = true;
        }, drawerTransitionMs);
    };

    const closeDrawers = () => {
        if (activeDrawer) {
            activeDrawer.classList.remove("open");
            activeDrawer.setAttribute("aria-hidden", "true");
            activeDrawer = null;
        }
        hideOverlay();
        document.body.classList.remove("drawer-open");
    };

    const openDrawer = (drawerToOpen) => {
        if (!drawerToOpen) return;
        if (activeDrawer === drawerToOpen) {
            closeDrawers();
            return;
        }

        if (activeDrawer && activeDrawer !== drawerToOpen) {
            activeDrawer.classList.remove("open");
            activeDrawer.setAttribute("aria-hidden", "true");
        }

        activeDrawer = drawerToOpen;
        showOverlay();
        drawerToOpen.classList.add("open");
        drawerToOpen.setAttribute("aria-hidden", "false");
        document.body.classList.add("drawer-open");
        drawerToOpen.dispatchEvent(new CustomEvent("drawer:open"));
    };

    if (overlay) {
        overlay.addEventListener("click", closeDrawers);
    }

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeDrawers);
    });

    if (notificationToggle) {
        notificationToggle.addEventListener("click", () => {
            openDrawer(notificationDrawer);
        });
    }

    if (searchToggle) {
        searchToggle.addEventListener("click", () => {
            openDrawer(searchDrawer);
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeDrawers();
            return;
        }

        const key = String(event.key || "").toLowerCase();
        if ((event.ctrlKey || event.metaKey) && key === "k") {
            const tagName = (event.target && event.target.tagName) ? event.target.tagName.toLowerCase() : "";
            if (tagName === "input" || tagName === "textarea") return;
            event.preventDefault();
            openDrawer(searchDrawer);
        }
    });
}

function setupDashboardRupyAssistant() {
    const assistantNode = document.querySelector("[data-rupy-dashboard]");
    if (!assistantNode) return;

    const messageNode = assistantNode.querySelector("[data-rupy-message]");
    const tipButton = assistantNode.querySelector("[data-rupy-tip-btn]");
    if (!messageNode) return;

    const parseNumeric = (rawValue) => {
        const normalized = String(rawValue ?? "").replace(/,/g, "").trim();
        const numericValue = Number(normalized);
        return Number.isFinite(numericValue) ? numericValue : 0;
    };

    const formatInr = (amount) => {
        const absoluteAmount = Math.abs(Number(amount) || 0);
        return `₹ ${new Intl.NumberFormat("en-IN", {
            maximumFractionDigits: 2,
        }).format(absoluteAmount)}`;
    };

    const coachPayload = parseJsonScript("rupy-coach-payload", null);
    const coachTips = Array.isArray(coachPayload?.tip_lines)
        ? coachPayload.tip_lines.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
    const coachPrimaryMessage = String(coachPayload?.primary_message || "").trim();
    const coachPrimaryState = String(coachPayload?.assistant_state || "").trim().toLowerCase();
    const assistantInitialState = String(assistantNode.dataset.rupyInitialState || coachPrimaryState || "")
        .trim()
        .toLowerCase();

    const budgetLeft = parseNumeric(assistantNode.dataset.budgetLeft);
    const totalBudget = parseNumeric(assistantNode.dataset.totalBudget);
    const totalSpent = parseNumeric(assistantNode.dataset.totalSpent);
    const spentPercent = parseNumeric(assistantNode.dataset.spentPercent);
    const forecastTotal = parseNumeric(assistantNode.dataset.forecastTotal);
    const forecastOver = parseNumeric(assistantNode.dataset.forecastOver);
    const forecastConfidence = String(assistantNode.dataset.forecastConfidence || "low").trim().toLowerCase();
    const currentMonth = String(assistantNode.dataset.currentMonth || "").trim() || "this month";
    const userName = String(assistantNode.dataset.userName || "").trim();
    const userFirstName = userName ? userName.split(/\s+/)[0] : "Friend";

    const stressLevel = inferRupyBudgetStressLevel({
        spentPercent,
        budgetLeft,
        forecastOver,
    });
    const celebrationTier = inferRupyCelebrationTier({
        spentPercent,
        budgetLeft,
        totalBudget,
        forecastOver,
    });
    applyRupyBudgetStressLevel(assistantNode, stressLevel);
    applyRupyCelebrationTier(assistantNode, celebrationTier);

    const assistantImageNode = assistantNode.querySelector("[data-rupy-dashboard-image]");
    const assistantMachine = createRupyStateMachine(assistantNode, {
        classPrefix: "state-",
        initialState: "idle",
        cooldownMs: 240,
    });
    const assistantImageMap = assistantImageNode
        ? {
            idle: String(assistantNode.dataset.rupyImgIdle || assistantImageNode.getAttribute("src") || "").trim(),
            thinking: String(assistantNode.dataset.rupyImgThinking || "").trim(),
            warning: String(assistantNode.dataset.rupyImgWarning || "").trim(),
            confused: String(assistantNode.dataset.rupyImgConfused || "").trim(),
            error: String(assistantNode.dataset.rupyImgError || "").trim(),
            celebrate: String(assistantNode.dataset.rupyImgCelebrate || "").trim(),
            proud: String(assistantNode.dataset.rupyImgProud || "").trim(),
        }
        : null;
    const assistantImageFallback = assistantImageMap?.idle || "";

    const assistantImageForState = (stateName) => {
        const normalized = String(stateName || "").trim().toLowerCase();
        if (!assistantImageMap) return "";
        if (normalized === "thinking" || normalized === "focus" || normalized === "peek") {
            return assistantImageMap.thinking || assistantImageFallback;
        }
        if (normalized === "warning" || normalized === "confused") {
            return assistantImageMap.confused || assistantImageMap.warning || assistantImageMap.error || assistantImageFallback;
        }
        if (normalized === "error" || normalized === "sleep") {
            return assistantImageMap.error || assistantImageMap.warning || assistantImageFallback;
        }
        if (normalized === "success" || normalized === "wave") {
            return assistantImageMap.proud || assistantImageMap.celebrate || assistantImageFallback;
        }
        if (normalized === "celebrate" || normalized === "money-rain") {
            return assistantImageMap.celebrate || assistantImageMap.proud || assistantImageFallback;
        }
        return assistantImageFallback;
    };

    const setAssistantImage = (stateName) => {
        if (!assistantImageNode || !assistantImageMap) return;
        const nextImage = assistantImageForState(stateName);
        if (!nextImage) return;
        const currentImage = String(assistantImageNode.getAttribute("src") || "").trim();
        if (currentImage === nextImage) return;
        assistantImageNode.setAttribute("src", nextImage);
    };

    const setAssistantState = (stateName, options = {}) => {
        const normalized = String(stateName || "").replace(/^state-/, "").trim().toLowerCase() || "idle";
        assistantMachine.transition(normalized, options);
        setAssistantImage(normalized);
    };
    let stopAssistantSequence = null;
    const playAssistantSequence = (steps) => {
        if (stopAssistantSequence) stopAssistantSequence();
        stopAssistantSequence = runRupyStateSequence((stateName, options = {}) => {
            setAssistantState(stateName, options);
        }, steps);
    };

    if (assistantImageMap) {
        const preloadSet = new Set(Object.values(assistantImageMap).filter(Boolean));
        preloadSet.forEach((src) => {
            const preloadImage = new Image();
            preloadImage.src = src;
        });
    }

    if (assistantImageNode) {
        assistantImageNode.addEventListener("error", () => {
            assistantNode.removeAttribute("data-rupy-has-images");
        });
    }

    const tipEntries = [];
    const seenTips = new Set();
    const pushTip = (text, { state = "", coach = false } = {}) => {
        const cleanText = String(text || "").trim();
        if (!cleanText) return;
        const key = cleanText.toLowerCase();
        if (seenTips.has(key)) return;
        seenTips.add(key);
        tipEntries.push({
            text: cleanText,
            state: String(state || "").trim().toLowerCase(),
            coach: Boolean(coach),
        });
    };

    pushTip(
        coachPrimaryMessage || `${userFirstName}, your ${currentMonth} dashboard is synced. I am tracking spending in real time.`,
        { state: assistantInitialState || coachPrimaryState || "idle", coach: true }
    );

    coachTips.forEach((tipText) => {
        pushTip(tipText, { coach: true });
    });

    if (totalSpent <= 0) {
        pushTip("This dashboard is fresh. Start with one expense and one income entry today.", { state: "thinking", coach: true });
        pushTip("Add your monthly budget in Settings first. It unlocks smarter alerts.", { state: "thinking", coach: true });
    }

    if (budgetLeft < 0) {
        pushTip(`Alert: You are over budget by ${formatInr(budgetLeft)}. Move to Settings and tighten category limits.`, { state: "error" });
    } else if (budgetLeft === 0) {
        pushTip("You have exactly reached your budget cap. Keep new expenses tightly controlled.", { state: "warning" });
    } else {
        pushTip(`Great control: ${formatInr(budgetLeft)} is still available. Keep this as buffer.`, { state: "success" });
    }

    if (spentPercent >= 95) {
        pushTip(`Spent ratio is ${spentPercent.toFixed(0)}%. Pause low-priority expenses for the rest of this month.`, { state: "warning" });
    } else if (spentPercent >= 75) {
        pushTip(`Spent ratio is ${spentPercent.toFixed(0)}%. Set a short daily cap to avoid month-end pressure.`, { state: "warning" });
    } else {
        pushTip(`Healthy pace: ${spentPercent.toFixed(0)}% of budget used. You are on track.`, { state: "success" });
    }

    if (forecastTotal > 0) {
        if (forecastOver > 0) {
            pushTip(`Forecast risk: projected total is ${formatInr(forecastTotal)}. Likely overspend of ${formatInr(forecastOver)}.`, { state: "error" });
        } else {
            pushTip(`Forecast confidence is ${forecastConfidence}. Projected month-end spend is ${formatInr(forecastTotal)}.`, { state: "thinking" });
        }
    }

    if (totalBudget > 0) {
        const suggestedDailyLimit = Math.max(0, (totalBudget - totalSpent) / 7);
        pushTip(`Action plan: stay near ${formatInr(suggestedDailyLimit)} per day for the next 7 days.`, { state: "thinking" });
    }

    pushTip("Weekly cut rule: trim one high-spend category first, then review reports for trend shifts.", { state: "thinking" });

    let activeTipIndex = 0;
    let autoRotateTimer = null;
    let sleepTimer = null;

    const inferStateFromTip = (tipText) => {
        const text = String(tipText || "").toLowerCase();
        if (text.includes("alert") || text.includes("overspend") || text.includes("risk")) return "error";
        if (text.includes("pace") || text.includes("cap") || text.includes("buffer")) return "warning";
        if (text.includes("great control") || text.includes("healthy pace") || text.includes("on track")) return "success";
        if (text.includes("action plan") || text.includes("weekly cut") || text.includes("forecast")) return "thinking";
        return "idle";
    };

    const playAssistantMood = (stateName, { coach = false } = {}) => {
        const normalized = String(stateName || "").trim().toLowerCase() || "idle";

        if (coach && (normalized === "thinking" || normalized === "idle")) {
            playAssistantSequence([
                { state: "wave", delayMs: 220 },
                { state: "thinking" },
            ]);
            return;
        }

        if (normalized === "success" || normalized === "celebrate" || normalized === "money-rain") {
            playAssistantSequence([
                { state: "thinking", delayMs: 140 },
                { state: "celebrate", delayMs: 360 },
                { state: normalized === "money-rain" ? "money-rain" : "success" },
            ]);
            return;
        }

        if (normalized === "warning") {
            playAssistantSequence([
                { state: "thinking", delayMs: 140 },
                { state: "warning" },
            ]);
            return;
        }

        if (normalized === "error") {
            playAssistantSequence([
                { state: "thinking", delayMs: 120 },
                { state: "warning", delayMs: 220 },
                { state: "error" },
            ]);
            return;
        }

        if (normalized === "thinking") {
            playAssistantSequence([{ state: "thinking" }]);
            return;
        }

        playAssistantSequence([{ state: "idle" }]);
    };

    const resetSleepTimer = () => {
        if (sleepTimer) {
            window.clearTimeout(sleepTimer);
            sleepTimer = null;
        }
        if (prefersReducedMotion()) return;
        sleepTimer = window.setTimeout(() => {
            setAssistantState("sleep");
        }, 20000);
    };

    const showTip = (index) => {
        const totalTips = tipEntries.length;
        if (!totalTips) return;

        const normalizedIndex = ((index % totalTips) + totalTips) % totalTips;
        activeTipIndex = normalizedIndex;
        const tipEntry = tipEntries[normalizedIndex] || {};
        const tipText = String(tipEntry.text || "").trim();
        if (!tipText) return;

        const explicitState = String(tipEntry.state || "").trim().toLowerCase();
        const inferredState = explicitState || inferStateFromTip(tipText);
        playAssistantMood(inferredState, { coach: Boolean(tipEntry.coach) });

        messageNode.classList.remove("is-updating");
        void messageNode.offsetWidth;
        messageNode.classList.add("is-updating");
        messageNode.textContent = tipText;

        assistantNode.classList.add("is-speaking");
        window.setTimeout(() => {
            assistantNode.classList.remove("is-speaking");
        }, 700);
        resetSleepTimer();
    };

    const startAutoRotate = () => {
        if (prefersReducedMotion() || tipEntries.length < 2) return;
        if (autoRotateTimer) window.clearInterval(autoRotateTimer);
        autoRotateTimer = window.setInterval(() => {
            showTip(activeTipIndex + 1);
        }, 9000);
    };

    const stopAutoRotate = () => {
        if (!autoRotateTimer) return;
        window.clearInterval(autoRotateTimer);
        autoRotateTimer = null;
    };

    if (tipButton) {
        tipButton.addEventListener("click", () => {
            playAssistantMood("celebrate");
            window.setTimeout(() => {
                showTip(activeTipIndex + 1);
            }, 220);
            startAutoRotate();
        });
    }

    assistantNode.addEventListener("mouseenter", () => {
        stopAutoRotate();
        if (assistantMachine.getState() === "sleep") {
            setAssistantState("idle");
        }
        resetSleepTimer();
    });
    assistantNode.addEventListener("mouseleave", () => {
        startAutoRotate();
        resetSleepTimer();
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            if (stopAssistantSequence) stopAssistantSequence();
            setAssistantState("sleep");
            stopAutoRotate();
            return;
        }
        setAssistantState("idle");
        startAutoRotate();
        resetSleepTimer();
    });

    showTip(0);
    startAutoRotate();
    resetSleepTimer();
}

function setupContextualRupyDialogues() {
    const pageRoot = document.querySelector("[data-rupy-context]");
    if (!pageRoot) return;

    const pageKeyRaw = String(pageRoot.dataset.rupyPage || document.body?.dataset?.endpoint || "").trim().toLowerCase();
    const pageKey = pageKeyRaw || "default";
    if (pageKey === "dashboard") return;
    const parseNumeric = (rawValue) => {
        const normalized = String(rawValue ?? "").replace(/,/g, "").trim();
        const numberValue = Number(normalized);
        return Number.isFinite(numberValue) ? numberValue : 0;
    };
    const formatInr = (amount) => {
        return `₹ ${new Intl.NumberFormat("en-IN", {
            maximumFractionDigits: 2,
        }).format(Math.abs(Number(amount) || 0))}`;
    };
    const forecastOver = parseNumeric(pageRoot.dataset.forecastOver);
    const budgetRemaining = parseNumeric(pageRoot.dataset.budgetRemaining);

    const dialogueLibrary = {
        expenses: [
            "Expenses page is live. Start by checking this week's cut suggestions.",
            "When adding a new transaction, watch category-limit percentages to avoid overshoot.",
            "Use month filter transitions to quickly spot recurring high-cost entries.",
        ],
        reports: [
            "Reports are most useful when paired with category limits and forecast signals.",
            "Focus first on the largest donut segment, then compare it to budget radar.",
            "If forecast risk is high, cut one top category this week and monitor trend shift.",
        ],
        settings: [
            "Set monthly budget first, then assign category limits for tighter control.",
            "Threshold + baseline tuning improves anomaly alerts quality significantly.",
            "Update limits monthly based on forecast and last month carry-forward.",
        ],
        account: [
            "Secure account setup complete. Keep password strong and unique.",
            "Profile details help keep notifications and export history aligned.",
            "Use quick preferences to switch theme/language without leaving your workflow.",
        ],
        default: [
            "Rupy is online and tracking smart actions for this page.",
            "Use contextual cards to stay ahead of budget and forecasting risk.",
            "Small weekly adjustments usually prevent month-end overspend.",
        ],
    };

    const tips = [...(dialogueLibrary[pageKey] || dialogueLibrary.default)];
    if (!Array.isArray(tips) || !tips.length) return;

    const hasEmptyStateSignals = Boolean(
        pageRoot.querySelector(".history-empty, .reports-empty-state, .reports-empty-copy")
    );
    if (hasEmptyStateSignals) {
        const coachTipByPage = {
            expenses: [
                "[coach] No records yet. Start with one expense and one income entry to activate trend tracking.",
                "[coach] Open Settings and set monthly budget so alerts can guide every new entry.",
            ],
            reports: [
                "[coach] Reports need category data. Add a few expenses first to unlock split analysis.",
                "[coach] Keep categories consistent this week so your charts become cleaner and more useful.",
            ],
            settings: [
                "[coach] Start from monthly budget, then add category limits for tighter control.",
                "[coach] Keep threshold tuning simple first, then optimize after one full month of data.",
            ],
            account: [
                "[coach] Add a profile photo and verify email so account identity is complete.",
            ],
            default: [
                "[coach] Start with one small action here and I will unlock smarter guidance next.",
            ],
        };
        const coachTips = coachTipByPage[pageKey] || coachTipByPage.default;
        tips.unshift(...coachTips);
    }

    if (forecastOver > 0) {
        tips.push(`Live signal: forecast risk is ${formatInr(forecastOver)} overspend unless pace changes.`);
    } else if (budgetRemaining > 0) {
        tips.push(`Live signal: budget buffer available is ${formatInr(budgetRemaining)}.`);
    }
    const contextImageMap = {
        idle: String(pageRoot.dataset.rupyImgIdle || "").trim(),
        thinking: String(pageRoot.dataset.rupyImgThinking || "").trim(),
        warning: String(pageRoot.dataset.rupyImgWarning || "").trim(),
        confused: String(pageRoot.dataset.rupyImgConfused || "").trim(),
        error: String(pageRoot.dataset.rupyImgError || "").trim(),
        celebrate: String(pageRoot.dataset.rupyImgCelebrate || "").trim(),
        proud: String(pageRoot.dataset.rupyImgProud || "").trim(),
    };
    const contextImageFallback = contextImageMap.idle;
    const hasContextImagePack = Boolean(contextImageFallback);
    const contextImageForState = (stateName) => {
        const normalized = String(stateName || "").trim().toLowerCase();
        if (!hasContextImagePack) return "";
        if (normalized === "thinking" || normalized === "focus" || normalized === "peek") {
            return contextImageMap.thinking || contextImageFallback;
        }
        if (normalized === "warning" || normalized === "confused") {
            return contextImageMap.confused || contextImageMap.warning || contextImageMap.error || contextImageFallback;
        }
        if (normalized === "error" || normalized === "sleep") {
            return contextImageMap.error || contextImageMap.warning || contextImageFallback;
        }
        if (normalized === "success" || normalized === "wave") {
            return contextImageMap.proud || contextImageMap.celebrate || contextImageFallback;
        }
        if (normalized === "celebrate") {
            return contextImageMap.celebrate || contextImageMap.proud || contextImageFallback;
        }
        return contextImageFallback;
    };
    const contextAvatarMarkup = hasContextImagePack
        ? `
            <img
                class="rupy-context-image"
                data-rupy-context-image
                src="${escapeHtml(contextImageFallback)}"
                alt=""
                loading="lazy"
                decoding="async"
            >
        `
        : `
            <span class="rupy-context-avatar-fallback" aria-hidden="true">
                <i class="fa-solid fa-indian-rupee-sign"></i>
            </span>
        `;

    let panelNode = pageRoot.querySelector("[data-rupy-context-panel]");
    if (!panelNode) {
        panelNode = document.createElement("section");
        panelNode.className = "rupy-context-panel";
        panelNode.setAttribute("data-rupy-context-panel", "");
        if (hasContextImagePack) panelNode.setAttribute("data-rupy-has-images", "true");
        panelNode.innerHTML = `
            <span class="rupy-context-avatar" aria-hidden="true">
                ${contextAvatarMarkup}
            </span>
            <div class="rupy-context-content">
                <span class="rupy-context-badge">Rupy Context</span>
                <p data-rupy-context-message>Rupy is preparing contextual guidance...</p>
            </div>
            <button type="button" class="rupy-context-next" data-rupy-context-next>
                <i class="fa-solid fa-comment-dots"></i>
                <span>Next insight</span>
            </button>
        `;

        const headerNode = pageRoot.querySelector(".header");
        if (headerNode) {
            headerNode.insertAdjacentElement("afterend", panelNode);
        } else {
            pageRoot.prepend(panelNode);
        }
    }
    if (hasContextImagePack) {
        panelNode.setAttribute("data-rupy-has-images", "true");
    }

    const messageNode = panelNode.querySelector("[data-rupy-context-message]");
    const nextButton = panelNode.querySelector("[data-rupy-context-next]");
    const contextImageNode = panelNode.querySelector("[data-rupy-context-image]");
    if (!messageNode) return;

    const panelMachine = createRupyStateMachine(panelNode, {
        classPrefix: "state-",
        initialState: "idle",
        cooldownMs: 220,
    });
    const setContextImage = (stateName) => {
        if (!contextImageNode || !hasContextImagePack) return;
        const nextImage = contextImageForState(stateName);
        if (!nextImage) return;
        const currentImage = String(contextImageNode.getAttribute("src") || "").trim();
        if (currentImage === nextImage) return;
        contextImageNode.setAttribute("src", nextImage);
    };
    const setPanelState = (stateName, options = {}) => {
        const normalized = String(stateName || "").replace(/^state-/, "").trim().toLowerCase() || "idle";
        panelMachine.transition(normalized, options);
        setContextImage(normalized);
    };
    let stopPanelSequence = null;
    const playPanelSequence = (steps) => {
        if (stopPanelSequence) stopPanelSequence();
        stopPanelSequence = runRupyStateSequence((stateName, options = {}) => {
            setPanelState(stateName, options);
        }, steps);
    };

    if (contextImageNode) {
        contextImageNode.addEventListener("error", () => {
            panelNode.removeAttribute("data-rupy-has-images");
        });
    }
    if (hasContextImagePack) {
        const preloadSet = new Set(Object.values(contextImageMap).filter(Boolean));
        preloadSet.forEach((src) => {
            const preloadImage = new Image();
            preloadImage.src = src;
        });
    }

    let tipIndex = 0;
    let rotateTimer = null;

    const inferState = (text, { isCoach = false } = {}) => {
        if (isCoach) return "wave";
        const content = String(text || "").toLowerCase();
        if (content.includes("risk") || content.includes("overspend") || content.includes("avoid")) return "error";
        if (content.includes("buffer")) return "success";
        if (content.includes("secure") || content.includes("strong")) return "success";
        if (content.includes("focus") || content.includes("check") || content.includes("set") || content.includes("start")) return "thinking";
        return "idle";
    };

    const playPanelMood = (stateName, { coach = false } = {}) => {
        const normalized = String(stateName || "").trim().toLowerCase() || "idle";

        if (coach) {
            playPanelSequence([
                { state: "wave", delayMs: 180 },
                { state: "thinking" },
            ]);
            return;
        }

        if (normalized === "success" || normalized === "celebrate") {
            playPanelSequence([
                { state: "thinking", delayMs: 120 },
                { state: "celebrate", delayMs: 320 },
                { state: "success" },
            ]);
            return;
        }

        if (normalized === "warning") {
            playPanelSequence([
                { state: "thinking", delayMs: 120 },
                { state: "warning" },
            ]);
            return;
        }

        if (normalized === "error") {
            playPanelSequence([
                { state: "thinking", delayMs: 120 },
                { state: "warning", delayMs: 220 },
                { state: "error" },
            ]);
            return;
        }

        if (normalized === "thinking") {
            playPanelSequence([
                { state: "thinking" },
            ]);
            return;
        }

        playPanelSequence([{ state: "idle" }]);
    };

    const renderTip = (nextIndex) => {
        const normalizedIndex = ((nextIndex % tips.length) + tips.length) % tips.length;
        tipIndex = normalizedIndex;
        const rawTip = String(tips[normalizedIndex] || "").trim();
        if (!rawTip) return;
        const isCoachTip = rawTip.startsWith("[coach]");
        const nextText = isCoachTip ? rawTip.replace(/^\[coach\]\s*/i, "") : rawTip;
        messageNode.classList.remove("is-updating");
        void messageNode.offsetWidth;
        messageNode.classList.add("is-updating");
        messageNode.textContent = nextText;
        const inferredState = inferState(nextText, { isCoach: isCoachTip });
        playPanelMood(inferredState, { coach: isCoachTip });
    };

    const startRotate = () => {
        if (prefersReducedMotion() || tips.length < 2) return;
        if (rotateTimer) window.clearInterval(rotateTimer);
        rotateTimer = window.setInterval(() => {
            renderTip(tipIndex + 1);
        }, 11000);
    };

    const stopRotate = () => {
        if (!rotateTimer) return;
        window.clearInterval(rotateTimer);
        rotateTimer = null;
    };

    if (nextButton) {
        nextButton.addEventListener("click", () => {
            playPanelMood("celebrate");
            window.setTimeout(() => {
                renderTip(tipIndex + 1);
            }, 180);
            startRotate();
        });
    }

    panelNode.addEventListener("mouseenter", stopRotate);
    panelNode.addEventListener("mouseleave", startRotate);

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            if (stopPanelSequence) stopPanelSequence();
            setPanelState("sleep");
            stopRotate();
            return;
        }
        setPanelState("idle");
        startRotate();
    });

    if (!String(messageNode.textContent || "").trim()) {
        messageNode.textContent = String(tips[0] || "").replace(/^\[coach\]\s*/i, "");
    }
    setPanelState("idle");
    renderTip(0);
    startRotate();
}

function setupPremiumDesktopPolish() {
    const pageRoot = document.querySelector(".premium-page");
    if (!pageRoot) return;

    const isDesktopLayout = window.matchMedia("(min-width: 1024px)").matches;
    if (!isDesktopLayout || prefersReducedMotion()) {
        pageRoot.classList.add("is-premium-ready");
        return;
    }

    const revealTargets = Array.from(
        pageRoot.querySelectorAll(".premium-header, .rupy-context-panel, .smart-insight-card, .card")
    );
    if (!revealTargets.length) {
        pageRoot.classList.add("is-premium-ready");
        return;
    }

    const uniqueTargets = Array.from(new Set(revealTargets));
    uniqueTargets.forEach((node, index) => {
        node.classList.add("premium-reveal");
        node.style.setProperty("--reveal-delay", `${Math.min(index * 45, 520)}ms`);
    });

    window.requestAnimationFrame(() => {
        uniqueTargets.forEach((node) => node.classList.add("is-visible"));
        pageRoot.classList.add("is-premium-ready");
    });
}

function setupGoalTemplateForm() {
    const formNode = document.querySelector("[data-goal-template-form]");
    if (!formNode) return;

    const templateSelect = formNode.querySelector("[data-goal-template-select]");
    const templateCardNodes = Array.from(formNode.querySelectorAll("[data-goal-template-card]"));
    const typeSelect = formNode.querySelector("[data-goal-type]");
    const titleInput = formNode.querySelector('input[name="title"]');
    const targetInput = formNode.querySelector("[data-goal-target]");
    const dueDateInput = formNode.querySelector("[data-goal-due-date]");
    const categorySelect = formNode.querySelector("[data-goal-category]");
    const trackingMonthInput = formNode.querySelector("[data-goal-tracking-month]");
    const recurringInput = formNode.querySelector("[data-goal-recurring]");

    let templates = [];
    try {
        templates = JSON.parse(String(formNode.getAttribute("data-goal-templates") || "[]"));
    } catch (_) {
        templates = [];
    }
    if (!Array.isArray(templates) || !templates.length) return;

    const templateMap = new Map();
    templates.forEach((item) => {
        if (!item || typeof item !== "object") return;
        const key = String(item.key || "").trim();
        if (!key) return;
        templateMap.set(key, item);
    });

    const setSelectedTemplateCard = (templateKey) => {
        if (!templateCardNodes.length) return;
        const selectedKey = String(templateKey || "").trim();
        templateCardNodes.forEach((node) => {
            const cardKey = String(node.getAttribute("data-goal-template-card") || "").trim();
            const isSelected = selectedKey ? cardKey === selectedKey : !cardKey;
            node.classList.toggle("is-selected", isSelected);
        });
    };

    const syncTypeUi = () => {
        if (!typeSelect) return;
        const goalType = String(typeSelect.value || "").trim().toLowerCase();
        const isSpendingCap = goalType === "spending_cap";

        if (categorySelect) {
            categorySelect.disabled = !isSpendingCap;
            if (!isSpendingCap) categorySelect.value = "";
        }
        if (trackingMonthInput) {
            trackingMonthInput.disabled = !isSpendingCap;
        }
        if (recurringInput) {
            recurringInput.disabled = !isSpendingCap;
            if (!isSpendingCap) recurringInput.checked = false;
        }
    };

    const applyTemplate = (templateKey) => {
        const template = templateMap.get(String(templateKey || "").trim());
        if (!template) return;

        if (templateSelect) {
            templateSelect.value = String(template.key || "").trim();
        }
        if (titleInput) titleInput.value = String(template.title || "").trim();
        if (typeSelect) typeSelect.value = String(template.goal_type || "").trim() || "savings";
        if (targetInput) targetInput.value = String(template.target_amount || "").trim();
        if (dueDateInput) dueDateInput.value = String(template.due_date || "").trim();
        if (categorySelect) categorySelect.value = String(template.category || "").trim();
        if (trackingMonthInput) trackingMonthInput.value = String(template.tracking_month || trackingMonthInput.value || "").trim();
        if (recurringInput) recurringInput.checked = Boolean(template.is_recurring);
        setSelectedTemplateCard(template.key);
        syncTypeUi();
    };

    if (templateSelect) {
        templateSelect.addEventListener("change", () => {
            const selectedKey = String(templateSelect.value || "").trim();
            if (!selectedKey) {
                setSelectedTemplateCard("");
                syncTypeUi();
                return;
            }
            applyTemplate(selectedKey);
        });
    }

    if (templateCardNodes.length) {
        templateCardNodes.forEach((node) => {
            node.addEventListener("click", () => {
                const templateKey = String(node.getAttribute("data-goal-template-card") || "").trim();
                if (!templateKey) {
                    if (templateSelect) templateSelect.value = "";
                    setSelectedTemplateCard("");
                    syncTypeUi();
                    return;
                }
                applyTemplate(templateKey);
            });
        });
    }

    if (typeSelect) {
        typeSelect.addEventListener("change", syncTypeUi);
    }

    if (templateSelect && String(templateSelect.value || "").trim()) {
        setSelectedTemplateCard(templateSelect.value);
    } else {
        setSelectedTemplateCard("");
    }
    syncTypeUi();
}

function setupRupySignalEmitter() {
    const signalNode = document.querySelector("[data-rupy-signal]");
    if (!signalNode) return;

    const parseNumber = (rawValue) => {
        const normalized = String(rawValue ?? "").replace(/,/g, "").trim();
        const numeric = Number(normalized);
        return Number.isFinite(numeric) ? numeric : 0;
    };

    const levelUp = String(signalNode.dataset.levelUp || "") === "1";
    const newAchievements = parseNumber(signalNode.dataset.newAchievements);
    const budgetWarning = String(signalNode.dataset.budgetWarning || "") === "1";
    const monthlyBudget = parseNumber(signalNode.dataset.monthlyBudget);
    const spentPercent = parseNumber(signalNode.dataset.monthlySpentPercent);
    const goalWarningCount = parseNumber(signalNode.dataset.goalWarningCount);
    const goalOverdueCount = parseNumber(signalNode.dataset.goalOverdueCount);
    const goalCompletedToday = parseNumber(signalNode.dataset.goalCompletedToday);
    const goalRecurringResets = parseNumber(signalNode.dataset.goalRecurringResets);
    const goalFocusTitle = String(signalNode.dataset.goalFocusTitle || "").trim();
    const goalEta = String(signalNode.dataset.goalEta || "").trim();
    const goalUiEventPayload = parseJsonScript("goal-ui-event", null);
    const goalUiEventType = goalUiEventPayload && typeof goalUiEventPayload === "object"
        ? String(goalUiEventPayload.type || "").trim().toLowerCase()
        : "";
    const suppressGoalCompletionSignal = goalUiEventType === "goal_completed";
    const suppressGoalWarningSignal = goalUiEventType === "goal_deadline_warning";
    const suppressGoalRecurringSignal = goalUiEventType === "goal_recurring_reset";
    const coachPayload = parseJsonScript("rupy-coach-payload", null);
    const coachTriggers = coachPayload && typeof coachPayload === "object" && coachPayload.triggers
        ? coachPayload.triggers
        : {};
    const coachMessages = coachPayload && typeof coachPayload === "object" && coachPayload.trigger_messages
        ? coachPayload.trigger_messages
        : {};
    const hasCoachTrigger = (key) => Boolean(coachTriggers && coachTriggers[key]);
    const coachMessage = (key, fallback = "") => {
        if (!coachMessages || typeof coachMessages !== "object") return String(fallback || "").trim();
        const value = String(coachMessages[key] || "").trim();
        return value || String(fallback || "").trim();
    };

    const emit = (type, message, delayMs = 0) => {
        window.setTimeout(() => {
            if (window.RupyMascot && typeof window.RupyMascot.emit === "function") {
                window.RupyMascot.emit(type, { message });
                return;
            }
            window.dispatchEvent(new CustomEvent("rupy:event", {
                detail: {
                    type,
                    message,
                },
            }));
        }, Math.max(220, delayMs));
    };

    if (levelUp) {
        emit("saving_money", "Bro you're leveling up your money skills!", 280);
    } else if (newAchievements > 0) {
        emit("saving_money", `Achievement unlocked x${newAchievements}. Rupy proud of you!`, 300);
    }

    if (budgetWarning) {
        emit("high_spending", `Bro... budget alert. ${spentPercent.toFixed(0)}% already used.`, 640);
    } else if (monthlyBudget > 0) {
        emit("budget_planning", "Budget planning mode on. Keep your daily cap active.", 690);
    }

    if (goalCompletedToday > 0 && !suppressGoalCompletionSignal) {
        const completionMessage = goalFocusTitle
            ? `Goal complete: ${goalFocusTitle}. Celebration unlocked.`
            : `Nice! ${goalCompletedToday} goal${goalCompletedToday > 1 ? "s" : ""} completed today.`;
        emit("saving_money", completionMessage, 260);
        showRupyToast(completionMessage, "success", 3400);
    }

    if (goalWarningCount > 0 && !suppressGoalWarningSignal) {
        const warningMessage = goalOverdueCount > 0
            ? `${goalOverdueCount} goal deadline${goalOverdueCount > 1 ? "s are" : " is"} overdue. ${goalEta || "Action needed now."}`
            : `${goalWarningCount} goal${goalWarningCount > 1 ? "s are" : " is"} near deadline. ${goalEta || "Review your goals plan."}`;
        emit("high_spending", warningMessage, goalCompletedToday > 0 ? 820 : 420);
        showRupyToast(`Rupy Warning: ${warningMessage}`, "warning", 3800);
    } else if (goalRecurringResets > 0 && !suppressGoalRecurringSignal) {
        const recurringMessage = `${goalRecurringResets} recurring goal${goalRecurringResets > 1 ? "s" : ""} reset for this month.`;
        emit("budget_planning", recurringMessage, 760);
        showRupyToast(`Rupy: ${recurringMessage}`, "info", 3200);
    }

    if (hasCoachTrigger("money_apprentice")) {
        const message = coachMessage("money_apprentice", "Money Apprentice unlocked. Mini celebration mode on.");
        emit("achievement_unlocked", message, 320);
        showRupyToast(message, "success", 3600);
    } else if (hasCoachTrigger("level_up") && levelUp) {
        const message = coachMessage("level_up", "Level up unlocked.");
        emit("saving_money", message, 320);
    }

    if (hasCoachTrigger("achievement_unlock") && newAchievements > 0 && !hasCoachTrigger("money_apprentice")) {
        const message = coachMessage("achievement_unlock", `Achievement unlocked x${newAchievements}.`);
        emit("saving_money", message, 380);
        showRupyToast(message, "success", 3400);
    }

    if (hasCoachTrigger("streak_reward")) {
        const message = coachMessage("streak_reward", "Streak reward unlocked.");
        emit("saving_money", message, 520);
        showRupyToast(message, "info", 3200);
    }

    if (hasCoachTrigger("no_spend_day")) {
        const message = coachMessage("no_spend_day", "No Spend Day complete.");
        emit("no_spend_day", message, 560);
        showRupyToast(message, "success", 3600);
    }

    if (hasCoachTrigger("inactive_24h")) {
        const message = coachMessage("inactive_24h", "No expense logged in 24h. Add today entry.");
        emit("user_inactive", message, 1120);
    }

    if (hasCoachTrigger("weekend_tip")) {
        const message = coachMessage("weekend_tip", "Weekend spending is high. Keep one cap active.");
        emit("tip", message, 760);
        showRupyToast(message, "info", 3200);
    }
}

function setupRupyMiniFinanceChatbot() {
    const rootNode = document.querySelector("[data-rupy-chat]");
    if (!rootNode) return;

    const drawerNode = document.querySelector("[data-rupy-chat-drawer]");
    const overlayNode = document.querySelector("[data-rupy-chat-overlay]");
    const menuItemNode = document.querySelector("[data-rupy-chat-menu-item]");
    const openButtons = Array.from(document.querySelectorAll("[data-rupy-chat-open]"));
    const closeButtons = Array.from(document.querySelectorAll("[data-rupy-chat-close]"));

    const logNode = rootNode.querySelector("[data-rupy-chat-log]");
    const formNode = rootNode.querySelector("[data-rupy-chat-form]");
    const inputNode = rootNode.querySelector("[data-rupy-chat-input]");
    const submitNode = rootNode.querySelector("[data-rupy-chat-submit]");
    const statusNode = rootNode.querySelector("[data-rupy-chat-status]");
    const quickNode = rootNode.querySelector("[data-rupy-chat-quick]");

    if (!logNode || !formNode || !inputNode) return;

    let defaultPrompts = [];
    try {
        defaultPrompts = JSON.parse(String(rootNode.dataset.rupyChatDefaultPrompts || "[]"));
    } catch (_) {
        defaultPrompts = [];
    }
    if (!Array.isArray(defaultPrompts) || !defaultPrompts.length) {
        defaultPrompts = [
            "How much did I spend today?",
            "Budget left this month?",
            "Show weekly summary",
            "How is my streak?",
        ];
    }

    const maxLogMessages = 16;
    const submitDefaultLabel = submitNode ? String(submitNode.textContent || "Ask Rupy").trim() : "Ask Rupy";
    let requestPending = false;
    const reducedMotion = prefersReducedMotion();
    const drawerTransitionMs = reducedMotion ? 1 : 220;
    let hideOverlayTimer = null;

    const isDrawerOpen = () => !drawerNode || drawerNode.classList.contains("open");

    const setMenuOpenState = (isOpen) => {
        if (menuItemNode) {
            menuItemNode.classList.toggle("is-open", Boolean(isOpen));
        }
        openButtons.forEach((button) => {
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
    };

    const openDrawer = () => {
        if (!drawerNode) return;

        if (hideOverlayTimer) {
            window.clearTimeout(hideOverlayTimer);
            hideOverlayTimer = null;
        }
        if (overlayNode) {
            overlayNode.hidden = false;
            window.requestAnimationFrame(() => {
                overlayNode.classList.add("open");
            });
        }

        drawerNode.classList.add("open");
        drawerNode.setAttribute("aria-hidden", "false");
        document.body.classList.add("rupy-chat-open");
        setMenuOpenState(true);

        window.setTimeout(() => {
            if (!requestPending) {
                inputNode.focus();
            }
        }, 120);
    };

    const closeDrawer = () => {
        if (drawerNode) {
            drawerNode.classList.remove("open");
            drawerNode.setAttribute("aria-hidden", "true");
        }
        if (overlayNode) {
            overlayNode.classList.remove("open");
            hideOverlayTimer = window.setTimeout(() => {
                overlayNode.hidden = true;
            }, drawerTransitionMs);
        }
        document.body.classList.remove("rupy-chat-open");
        setMenuOpenState(false);
    };

    const contextStorageKey = "expensepro-rupy-chat-context";
    let chatContext = (() => {
        try {
            const rawValue = sessionStorage.getItem(contextStorageKey);
            if (!rawValue) return null;
            const parsed = JSON.parse(rawValue);
            return (parsed && typeof parsed === "object") ? parsed : null;
        } catch (_) {
            return null;
        }
    })();

    const stateToEvent = (stateName) => {
        const normalized = String(stateName || "").trim().toLowerCase();
        if (normalized === "money-rain") return "no_spend_day";
        if (normalized === "celebration") return "saving_money";
        if (normalized === "warning" || normalized === "error") return "high_spending";
        if (normalized === "happy") return "budget_under_control";
        if (normalized === "thinking") return "budget_planning";
        return "tip";
    };

    const emitMascotEvent = (type, message) => {
        const cleanType = String(type || "").trim().toLowerCase();
        const cleanMessage = String(message || "").trim();
        if (!cleanType) return;

        if (window.RupyMascot && typeof window.RupyMascot.emit === "function") {
            window.RupyMascot.emit(cleanType, { message: cleanMessage });
            return;
        }

        window.dispatchEvent(new CustomEvent("rupy:event", {
            detail: {
                type: cleanType,
                message: cleanMessage,
            },
        }));
    };

    const setStatus = (message = "", { error = false } = {}) => {
        if (!statusNode) return;
        const cleanMessage = String(message || "").trim();
        if (!cleanMessage) {
            statusNode.hidden = true;
            statusNode.textContent = "";
            statusNode.classList.remove("is-error");
            return;
        }
        statusNode.hidden = false;
        statusNode.textContent = cleanMessage;
        statusNode.classList.toggle("is-error", Boolean(error));
    };

    const trimLog = () => {
        while (logNode.children.length > maxLogMessages) {
            const firstMessage = logNode.firstElementChild;
            if (!firstMessage) break;
            firstMessage.remove();
        }
    };

    const appendMessage = (role, text) => {
        const cleanRole = String(role || "").trim().toLowerCase() === "user" ? "user" : "rupy";
        const cleanText = String(text || "").trim();
        if (!cleanText) return;

        const wrapper = document.createElement("article");
        wrapper.className = `rupy-chat-msg ${cleanRole === "user" ? "is-user" : "is-rupy"}`;

        const authorNode = document.createElement("span");
        authorNode.className = "rupy-chat-author";
        authorNode.textContent = cleanRole === "user" ? "You" : "Rupy";

        const copyNode = document.createElement("p");
        copyNode.textContent = cleanText;

        wrapper.appendChild(authorNode);
        wrapper.appendChild(copyNode);
        logNode.appendChild(wrapper);
        trimLog();
        logNode.scrollTop = logNode.scrollHeight;
    };

    const setPending = (isPending) => {
        requestPending = Boolean(isPending);
        inputNode.disabled = requestPending;
        if (submitNode) {
            submitNode.disabled = requestPending;
            submitNode.textContent = requestPending ? "Rupy..." : submitDefaultLabel;
        }
        if (!requestPending && isDrawerOpen()) {
            inputNode.focus();
        }
    };

    const renderQuickPrompts = (prompts) => {
        if (!quickNode) return;
        const source = Array.isArray(prompts) && prompts.length ? prompts : defaultPrompts;
        quickNode.innerHTML = "";
        source
            .map((item) => String(item || "").trim())
            .filter(Boolean)
            .slice(0, 4)
            .forEach((promptText) => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "rupy-chat-quick-btn";
                button.setAttribute("data-rupy-chat-prompt", promptText);
                button.textContent = promptText;
                quickNode.appendChild(button);
            });
    };

    const sendQuestion = async (question) => {
        const cleanQuestion = String(question || "").trim();
        if (!cleanQuestion || requestPending) return;

        appendMessage("user", cleanQuestion);
        inputNode.value = "";
        setStatus("Rupy is thinking...");
        setPending(true);

        try {
            // VIVA: FRONTEND API - send the user's question to the backend Rupy chat endpoint.
            const response = await fetch("/api/rupy/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({
                    question: cleanQuestion,
                    context: chatContext || undefined,
                }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || !payload.ok) {
                throw new Error(String(payload.error || "Could not fetch chat response."));
            }

            const answer = String(payload.answer || "").trim() || "No response available right now.";
            const state = String(payload.state || "thinking").trim().toLowerCase();
            const eventType = String(payload.event_type || stateToEvent(state)).trim().toLowerCase();
            appendMessage("rupy", answer);
            emitMascotEvent(eventType || stateToEvent(state), answer);
            if (payload.context_update && typeof payload.context_update === "object") {
                chatContext = payload.context_update;
                try {
                    sessionStorage.setItem(contextStorageKey, JSON.stringify(chatContext));
                } catch (_) {
                    // Ignore storage write failures.
                }
            }
            renderQuickPrompts(payload.quick_replies);
            setStatus("");
        } catch (_) {
            const fallbackMessage = "Rupy service unavailable right now. Try again in a moment.";
            appendMessage("rupy", fallbackMessage);
            setStatus("Could not connect to Rupy.", { error: true });
            showRupyToast("Could not connect to Rupy chat.", "error", 3200);
        } finally {
            setPending(false);
        }
    };

    formNode.addEventListener("submit", (event) => {
        event.preventDefault();
        const question = String(inputNode.value || "").trim();
        if (!question) {
            setStatus("Type a question first.");
            inputNode.focus();
            return;
        }
        void sendQuestion(question);
    });

    if (quickNode) {
        quickNode.addEventListener("click", (event) => {
            const button = event.target.closest("[data-rupy-chat-prompt]");
            if (!button || requestPending) return;
            const prompt = String(button.getAttribute("data-rupy-chat-prompt") || "").trim();
            if (!prompt) return;
            void sendQuestion(prompt);
        });
    }

    openButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            if (isDrawerOpen()) {
                closeDrawer();
                return;
            }
            openDrawer();
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeDrawer);
    });

    if (overlayNode) {
        overlayNode.addEventListener("click", closeDrawer);
    }

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if (isDrawerOpen()) {
            closeDrawer();
        }
    });

    renderQuickPrompts(defaultPrompts);
    setStatus("");
    setMenuOpenState(false);
}

function setupRupyMemeGenerator() {
    const rootNode = document.querySelector("[data-rupy-meme-generator]");
    if (!rootNode) return;

    const canvasNode = rootNode.querySelector("[data-rupy-meme-canvas]");
    if (!canvasNode) return;
    const context = canvasNode.getContext("2d");
    if (!context) return;

    const uploadInput = rootNode.querySelector("[data-rupy-meme-upload]");
    const templateSelect = rootNode.querySelector("[data-rupy-meme-template]");
    const expressionSelect = rootNode.querySelector("[data-rupy-meme-expression]");
    const customInput = rootNode.querySelector("[data-rupy-meme-custom]");
    const renderButton = rootNode.querySelector("[data-rupy-meme-render]");
    const downloadButton = rootNode.querySelector("[data-rupy-meme-download]");
    const shareButton = rootNode.querySelector("[data-rupy-meme-share]");
    const statusNode = rootNode.querySelector("[data-rupy-meme-status]");

    let expressionList = [];
    try {
        expressionList = JSON.parse(String(rootNode.getAttribute("data-rupy-meme-expressions") || "[]"));
    } catch (_) {
        expressionList = [];
    }

    const expressionMap = {};
    if (Array.isArray(expressionList)) {
        expressionList.forEach((item) => {
            if (!item || typeof item !== "object") return;
            const key = String(item.key || "").trim().toLowerCase();
            const src = String(item.src || "").trim();
            if (!key || !src) return;
            expressionMap[key] = src;
        });
    }

    const fallbackExpressionMap = {
        warning: String(rootNode.dataset.rupyMemeImgWarning || "").trim(),
        happy: String(rootNode.dataset.rupyMemeImgHappy || "").trim(),
        thinking: String(rootNode.dataset.rupyMemeImgThinking || "").trim(),
        lazy_rich: String(rootNode.dataset.rupyMemeImgLazy || "").trim(),
        broke: String(rootNode.dataset.rupyMemeImgBroke || "").trim(),
        idle: String(rootNode.dataset.rupyMemeImgIdle || "").trim(),
    };
    Object.entries(fallbackExpressionMap).forEach(([key, src]) => {
        if (!src || expressionMap[key]) return;
        expressionMap[key] = src;
    });

    const expressionKeys = Object.keys(expressionMap);
    if (expressionSelect && !expressionSelect.options.length && expressionKeys.length) {
        expressionKeys.forEach((key) => {
            const option = document.createElement("option");
            option.value = key;
            option.textContent = key.replace(/[_-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
            expressionSelect.appendChild(option);
        });
    }

    const defaultExpressionKey = expressionMap.warning
        ? "warning"
        : (expressionKeys[0] || "idle");
    if (expressionSelect) {
        const selectedKey = String(expressionSelect.value || "").trim().toLowerCase();
        if (!selectedKey || !expressionMap[selectedKey]) {
            expressionSelect.value = defaultExpressionKey;
        }
    }

    const fallbackExpression = expressionMap[defaultExpressionKey] || expressionMap.idle || "";

    let uploadedImageSrc = "";
    const imageCache = new Map();

    const setStatus = (message) => {
        if (!statusNode) return;
        const text = String(message || "").trim();
        if (!text) return;
        statusNode.textContent = text;
    };

    const loadImage = (src) => {
        const key = String(src || "").trim();
        if (!key) {
            return Promise.reject(new Error("Image source missing"));
        }
        if (imageCache.has(key)) {
            return Promise.resolve(imageCache.get(key));
        }
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => {
                imageCache.set(key, image);
                resolve(image);
            };
            image.onerror = () => reject(new Error(`Could not load image: ${key}`));
            image.src = key;
        });
    };

    const readFileAsDataUrl = (file) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error("Could not read file"));
            reader.readAsDataURL(file);
        });
    };

    const canvasToBlob = () => {
        return new Promise((resolve, reject) => {
            canvasNode.toBlob((blob) => {
                if (!blob) {
                    reject(new Error("Could not generate image blob"));
                    return;
                }
                resolve(blob);
            }, "image/png");
        });
    };

    const getActiveCaption = () => {
        const selectedTemplate = String(templateSelect?.value || "").trim();
        const customCaption = String(customInput?.value || "").trim();
        return customCaption || selectedTemplate || "Rupy Reacts";
    };

    const wrapCaption = (text, maxWidth) => {
        const content = String(text || "").trim();
        if (!content) return [];
        const words = content.split(/\s+/);
        const lines = [];
        let currentLine = "";

        words.forEach((word) => {
            const nextLine = currentLine ? `${currentLine} ${word}` : word;
            const width = context.measureText(nextLine).width;
            if (width > maxWidth && currentLine) {
                lines.push(currentLine);
                currentLine = word;
                return;
            }
            currentLine = nextLine;
        });

        if (currentLine) lines.push(currentLine);
        return lines.slice(0, 3);
    };

    const drawRoundedRect = (x, y, width, height, radius) => {
        const safeRadius = Math.min(radius, width / 2, height / 2);
        context.beginPath();
        context.moveTo(x + safeRadius, y);
        context.arcTo(x + width, y, x + width, y + height, safeRadius);
        context.arcTo(x + width, y + height, x, y + height, safeRadius);
        context.arcTo(x, y + height, x, y, safeRadius);
        context.arcTo(x, y, x + width, y, safeRadius);
        context.closePath();
    };

    const renderMeme = async () => {
        const selectedExpression = String(expressionSelect?.value || defaultExpressionKey).trim().toLowerCase();
        const expressionSrc = expressionMap[selectedExpression] || fallbackExpression;
        if (!expressionSrc) {
            setStatus("Expression image missing.");
            return;
        }

        const selectedTemplate = String(templateSelect?.value || "").trim();
        const customCaption = String(customInput?.value || "").trim();
        const caption = customCaption || selectedTemplate || "Budget left the chat.";

        try {
            const mascotImage = await loadImage(expressionSrc);
            const screenshotImage = uploadedImageSrc ? await loadImage(uploadedImageSrc) : null;

            const width = canvasNode.width;
            const height = canvasNode.height;

            const gradient = context.createLinearGradient(0, 0, width, height);
            gradient.addColorStop(0, "#f8fafc");
            gradient.addColorStop(1, "#dbeafe");
            context.fillStyle = gradient;
            context.fillRect(0, 0, width, height);

            drawRoundedRect(30, 30, width - 60, height - 60, 28);
            context.save();
            context.clip();
            context.fillStyle = "rgba(255, 255, 255, 0.82)";
            context.fillRect(30, 30, width - 60, height - 60);
            context.restore();

            if (screenshotImage) {
                drawRoundedRect(54, 365, width - 108, 440, 22);
                context.save();
                context.clip();
                context.drawImage(screenshotImage, 54, 365, width - 108, 440);
                context.restore();
            } else {
                drawRoundedRect(54, 365, width - 108, 440, 22);
                context.save();
                context.clip();
                const fallbackGradient = context.createLinearGradient(0, 365, width, 805);
                fallbackGradient.addColorStop(0, "#dbeafe");
                fallbackGradient.addColorStop(1, "#bfdbfe");
                context.fillStyle = fallbackGradient;
                context.fillRect(54, 365, width - 108, 440);
                context.restore();
                context.fillStyle = "#1e3a8a";
                context.font = '600 24px "Outfit", "Manrope", sans-serif';
                context.fillText("Upload screenshot to include expense preview", 94, 590);
            }

            context.drawImage(mascotImage, 72, 92, 250, 250);

            context.fillStyle = "#0f172a";
            context.font = '800 50px "Outfit", "Manrope", sans-serif';
            context.textAlign = "left";
            context.textBaseline = "top";
            const lines = wrapCaption(caption, width - 372);
            lines.forEach((line, index) => {
                context.fillText(line, 336, 126 + (index * 60));
            });

            context.fillStyle = "#1d4ed8";
            context.font = '700 26px "Outfit", "Manrope", sans-serif';
            context.fillText("Rupy Reacts", 336, 84);

            context.fillStyle = "#0f172a";
            context.font = '600 23px "Outfit", "Manrope", sans-serif';
            context.fillText("ExpensePro Meme Lab", 58, 835);

            setStatus("Meme generated. Download and share.");
        } catch (_) {
            setStatus("Could not generate meme. Try another image.");
        }
    };

    if (uploadInput) {
        uploadInput.addEventListener("change", async () => {
            const selectedFile = uploadInput.files && uploadInput.files[0];
            if (!selectedFile) return;
            try {
                uploadedImageSrc = await readFileAsDataUrl(selectedFile);
                setStatus("Screenshot loaded.");
            } catch (_) {
                uploadedImageSrc = "";
                setStatus("Could not load selected image.");
            }
        });
    }

    if (renderButton) {
        renderButton.addEventListener("click", () => {
            void renderMeme();
        });
    }

    if (downloadButton) {
        downloadButton.addEventListener("click", () => {
            try {
                const link = document.createElement("a");
                link.href = canvasNode.toDataURL("image/png");
                link.download = "rupy-meme.png";
                link.click();
                setStatus("Meme downloaded.");
            } catch (_) {
                setStatus("Download failed. Regenerate and retry.");
            }
        });
    }

    if (shareButton) {
        shareButton.addEventListener("click", async () => {
            const caption = getActiveCaption();
            try {
                await renderMeme();
                const blob = await canvasToBlob();
                const memeFile = new File([blob], "rupy-meme.png", { type: "image/png" });

                if (navigator.share && navigator.canShare && navigator.canShare({ files: [memeFile] })) {
                    await navigator.share({
                        title: "Rupy Meme",
                        text: caption,
                        files: [memeFile],
                    });
                    setStatus("Meme shared successfully.");
                    return;
                }

                if (navigator.share) {
                    await navigator.share({
                        title: "Rupy Meme",
                        text: caption,
                    });
                    setStatus("Meme shared successfully.");
                    return;
                }

                if (navigator.clipboard && window.ClipboardItem) {
                    const clipboardItem = new ClipboardItem({
                        [blob.type]: blob,
                    });
                    await navigator.clipboard.write([clipboardItem]);
                    setStatus("Meme image copied to clipboard. Paste it anywhere.");
                    return;
                }

                if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
                    await navigator.clipboard.writeText(caption);
                    setStatus("Share API unavailable. Caption copied to clipboard.");
                    return;
                }

                setStatus("Sharing is not supported on this browser.");
            } catch (error) {
                if (error && error.name === "AbortError") {
                    setStatus("Share canceled.");
                    return;
                }
                setStatus("Share failed. Try download instead.");
            }
        });
    }

    if (templateSelect) {
        templateSelect.addEventListener("change", () => {
            if (!customInput) return;
            if (String(customInput.value || "").trim()) return;
            customInput.setAttribute("placeholder", String(templateSelect.value || "").trim());
        });
    }

    void renderMeme();
}

document.addEventListener("DOMContentLoaded", () => {
    setupAppPageEntrance();
    setupLanguageLocalization();
    setupSplashIntro();
    setupToastSystem();
    setupGoalUiEvent();
    setupContextualRupyDialogues();
    setupAuthLoginFlow();
    setupLoginRupyMascot();
    setupProfileDropdown();
    setupAppearanceQuickControls();
    setupSidebarToggle();
    setupSidebarBrandCoinSpin();
    setupPasswordToggles();
    setupAccountAvatarPreview();
    setupLogoutConfirmation();
    setupActionConfirmModal();
    setupCategorySelects();
    setupDashboardIntro();
    setupHistoryFilterTransitions();
    setupDashboardDrawers();
    setupDashboardRupyAssistant();
    setupGoalTemplateForm();
    setupRupySignalEmitter();
    setupRupyMiniFinanceChatbot();
    setupRupyMemeGenerator();
    setupPremiumDesktopPolish();
});

