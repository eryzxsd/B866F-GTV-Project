package com.local.b866f.notificationcards;

import android.accessibilityservice.AccessibilityService;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.service.notification.StatusBarNotification;
import android.view.KeyEvent;
import android.view.ViewConfiguration;
import android.view.accessibility.AccessibilityEvent;

/** Only owns a Home key sequence that starts while a card is visible. */
public final class HomeKeyService extends AccessibilityService {
    private static boolean connected;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private StatusBarNotification pending;
    private boolean tracking, held;
    private Runnable pendingOpen;
    private int homeDowns, detailOpens, shortHomes;
    static boolean isConnected() { return connected; }
    private final Runnable hold = new Runnable() { public void run() { if (tracking) held = true; } };

    @Override protected void onServiceConnected() { connected = true; }
    private void openDetails(StatusBarNotification notification) {
        if (notification == null || !CardListener.isActive(notification.getKey())) return;
        NotificationDetailsActivity.pending = notification;
        try {
            startActivity(new Intent(this, NotificationDetailsActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP));
            detailOpens++; CardListener.hideCurrentCard();
        } catch (RuntimeException ignored) { NotificationDetailsActivity.pending = null; }
    }
    @Override protected boolean onKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN && pendingOpen != null
                && (event.getKeyCode() == KeyEvent.KEYCODE_BACK || event.getKeyCode() == KeyEvent.KEYCODE_HOME)) {
            ui.removeCallbacks(pendingOpen); pendingOpen = null;
        }
        if (event.getKeyCode() != KeyEvent.KEYCODE_HOME) return false;
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            homeDowns++;
            if (!tracking) {
                if (event.getRepeatCount() != 0) return false;
                pending = CardListener.currentCard();
                if (pending == null) return false;
                tracking = true; held = false;
                ui.postDelayed(hold, ViewConfiguration.getLongPressTimeout());
            } else if (event.isLongPress()) { held = true; }
            return true;
        }
        if (event.getAction() == KeyEvent.ACTION_UP && tracking) {
            ui.removeCallbacks(hold);
            boolean home = !held && !event.isCanceled();
            final StatusBarNotification selected = held && !event.isCanceled() ? pending : null;
            reset();
            if (selected != null) {
                CardListener.hideCurrentCard();
                // This vendor policy launches ALL_APPS before accessibility can consume Home.
                // Let that one system action settle, then open once. Never fight the user's Back.
                pendingOpen = new Runnable() { public void run() { pendingOpen = null; openDetails(selected); } };
                ui.postDelayed(pendingOpen, 600);
            } else if (home) {
                // Clear the card first so the injected global Home action cannot be recaptured.
                CardListener.hideCurrentCard(); shortHomes++; performGlobalAction(GLOBAL_ACTION_HOME);
            }
            return true;
        }
        return false;
    }
    private void reset() { ui.removeCallbacks(hold); pending = null; tracking = false; held = false; }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }
    @Override protected void dump(java.io.FileDescriptor fd, java.io.PrintWriter writer, String[] args) {
        writer.println("connected=" + connected + " homeDowns=" + homeDowns
                + " detailOpens=" + detailOpens + " shortHomes=" + shortHomes + " tracking=" + tracking);
    }
    @Override public void onInterrupt() {
        reset(); if (pendingOpen != null) { ui.removeCallbacks(pendingOpen); pendingOpen = null; }
    }
    @Override public void onDestroy() { connected = false; reset(); ui.removeCallbacksAndMessages(null); super.onDestroy(); }
}
