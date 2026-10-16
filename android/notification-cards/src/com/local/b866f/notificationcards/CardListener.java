package com.local.b866f.notificationcards;

import android.app.KeyguardManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.provider.Settings;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.LinkedHashMap;
import java.util.Map;

/** Local, passive TV cards. No input interception, root, networking, or content logging. */
public final class CardListener extends NotificationListenerService {
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final Map<String, String> seen = new LinkedHashMap<String, String>() {
        private static final long serialVersionUID = 1L;
        protected boolean removeEldestEntry(Map.Entry<String, String> e) { return size() > 64; }
    };
    private View card;
    private String displayedKey;
    private long lastShown;
    private final Runnable hideTask = new Runnable() { public void run() { hide(); } };

    @Override public void onNotificationPosted(final StatusBarNotification sbn, final RankingMap ranks) {
        if (sbn == null || !sbn.getUser().equals(android.os.Process.myUserHandle())) return;
        final Notification n = sbn.getNotification();
        String pkg = sbn.getPackageName();
        // Google TV owns its own card pipeline; never duplicate or replace those alerts.
        if (pkg.equals("com.google.android.apps.tv.launcherx") || pkg.equals("android")
                || pkg.equals("com.android.systemui") || pkg.equals("com.control.device")) return;
        if (pkg.equals(getPackageName()) && !"b866f_preview".equals(sbn.getTag())) return;
        if ((n.flags & (Notification.FLAG_ONGOING_EVENT | Notification.FLAG_FOREGROUND_SERVICE
                | Notification.FLAG_GROUP_SUMMARY)) != 0 || n.visibility == Notification.VISIBILITY_SECRET) return;
        if (Notification.CATEGORY_TRANSPORT.equals(n.category)) return;
        Ranking rank = new Ranking();
        int importance = ranks != null && ranks.getRanking(sbn.getKey(), rank)
                ? rank.getImportance() : NotificationManager.IMPORTANCE_DEFAULT;
        Bundle tv = n.extras.getBundle("android.tv.EXTENSIONS");
        if (tv != null && (tv.getInt("flags", 0) & 2) != 0) return;
        // Normal TV notifications, or an explicitly high-priority non-TV alert.
        if (importance < NotificationManager.IMPORTANCE_DEFAULT
                || (tv == null && importance < NotificationManager.IMPORTANCE_HIGH)) return;
        final String title = text(n.extras.getCharSequence(Notification.EXTRA_TITLE), 160);
        final String body = text(n.extras.getCharSequence(Notification.EXTRA_TEXT), 320);
        if (title.length() == 0 && body.length() == 0) return;
        ui.post(new Runnable() { public void run() { show(sbn, title, body); } });
    }

    private static String text(CharSequence s, int limit) {
        if (s == null) return "";
        String v = s.toString().trim();
        return v.length() <= limit ? v : v.substring(0, limit);
    }
    // Match TV's 1280x720 design canvas even when this firmware gives apps phone density.
    private float unit() {
        android.util.DisplayMetrics m = getResources().getDisplayMetrics();
        return Math.min(m.widthPixels / 1280f, m.heightPixels / 720f);
    }
    private int dp(float n) { return Math.round(n * unit()); }
    private GradientDrawable background(int color, int radius) {
        GradientDrawable d = new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(radius)); return d;
    }
    private TextView label(String s, int sp, int color, boolean bold, int lines) {
        TextView v = new TextView(this); v.setText(s);
        v.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX,
                sp * unit() * getResources().getConfiguration().fontScale); v.setTextColor(color);
        v.setMaxLines(lines); v.setEllipsize(android.text.TextUtils.TruncateAt.END);
        if (bold) v.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        v.setIncludeFontPadding(false); return v;
    }
    private void show(StatusBarNotification sbn, String title, String body) {
        PowerManager power = (PowerManager)getSystemService(POWER_SERVICE);
        KeyguardManager lock = (KeyguardManager)getSystemService(KEYGUARD_SERVICE);
        if (!Settings.canDrawOverlays(this) || !power.isInteractive() || lock.isKeyguardLocked()) return;
        String fingerprint = title + "\n" + body;
        if (fingerprint.equals(seen.get(sbn.getKey()))) return;
        long now = SystemClock.elapsedRealtime();
        if (lastShown != 0 && now - lastShown < 1500) return;
        seen.put(sbn.getKey(), fingerprint); lastShown = now;
        hide();
        LinearLayout box = new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL);
        box.setBackground(background(Color.rgb(30, 33, 34), 28)); box.setElevation(dp(8));
        LinearLayout row = new LinearLayout(this); row.setPadding(dp(16), dp(16), dp(18), dp(14));
        row.setGravity(Gravity.TOP);
        ImageView icon = new ImageView(this); icon.setPadding(dp(10), dp(10), dp(10), dp(10));
        icon.setBackground(background(Color.rgb(41, 46, 47), 24));
        try {
            Drawable d = sbn.getNotification().getSmallIcon() == null ? null
                    : sbn.getNotification().getSmallIcon().loadDrawable(this);
            icon.setImageDrawable(d);
            icon.setImageTintList(android.content.res.ColorStateList.valueOf(Color.rgb(232, 239, 240)));
        } catch (RuntimeException ignored) { icon.setImageResource(android.R.drawable.ic_dialog_info); }
        row.addView(icon, new LinearLayout.LayoutParams(dp(40), dp(40)));
        LinearLayout words = new LinearLayout(this); words.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams wp = new LinearLayout.LayoutParams(0, -2, 1); wp.leftMargin = dp(12);
        if (title.length() > 0) words.addView(label(title, 16, Color.rgb(233, 239, 240), true, 2));
        if (body.length() > 0) {
            TextView desc = label(body, 14, Color.rgb(171, 178, 179), false, 2);
            LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, -2); bp.topMargin = dp(4);
            words.addView(desc, bp);
        }
        row.addView(words, wp); box.addView(row);
        View divider = new View(this); divider.setBackgroundColor(Color.rgb(52, 57, 58));
        box.addView(divider, new LinearLayout.LayoutParams(-1, dp(1)));
        String app = sbn.getPackageName();
        try { app = getPackageManager().getApplicationLabel(getPackageManager().getApplicationInfo(app, 0)).toString(); }
        catch (Exception ignored) { }
        TextView footer = label("Notifikasi dari " + app, 13, Color.rgb(171, 178, 179), false, 1);
        footer.setPadding(dp(16), dp(10), dp(16), dp(12)); box.addView(footer);
        WindowManager wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        int width = Math.min(dp(376), getResources().getDisplayMetrics().widthPixels - dp(40));
        WindowManager.LayoutParams params = new WindowManager.LayoutParams(width, -2,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
                android.graphics.PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP | Gravity.RIGHT; params.x = dp(32); params.y = dp(32);
        params.setTitle("B866F notification card");
        try { wm.addView(box, params); card = box; displayedKey = sbn.getKey(); ui.postDelayed(hideTask, 6500); }
        catch (RuntimeException ignored) { hide(); }
    }
    private void hide() {
        ui.removeCallbacks(hideTask);
        if (card != null) {
            try { ((WindowManager)getSystemService(WINDOW_SERVICE)).removeViewImmediate(card); }
            catch (RuntimeException ignored) { }
        }
        card = null; displayedKey = null;
    }
    @Override public void onNotificationRemoved(final StatusBarNotification sbn) {
        if (sbn == null) return;
        ui.post(new Runnable() { public void run() {
            seen.remove(sbn.getKey()); if (sbn.getKey().equals(displayedKey)) hide();
        } });
    }
    @Override public void onListenerDisconnected() { hide(); seen.clear(); super.onListenerDisconnected(); }
    @Override public void onDestroy() { hide(); ui.removeCallbacksAndMessages(null); super.onDestroy(); }
}
