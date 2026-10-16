package com.local.b866f.notificationcards;

import android.app.Activity;
import android.app.Notification;
import android.app.PendingIntent;
import android.graphics.Color;
import android.os.Bundle;
import android.service.notification.StatusBarNotification;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** A local detail panel, only opened by a deliberate Home hold during a card. */
public final class NotificationDetailsActivity extends Activity {
    static StatusBarNotification pending;
    static boolean visible;
    private StatusBarNotification item;
    private int dp(int x) { return Math.round(x * getResources().getDisplayMetrics().heightPixels / 720f); }
    private TextView label(CharSequence s, int sp, int color) {
        TextView v = new TextView(this); v.setText(s == null ? "" : s); v.setTextSize(sp); v.setTextColor(color);
        v.setPadding(0, 0, 0, dp(14)); return v;
    }
    private Button button(String title) {
        Button b = new Button(this); b.setText(title); b.setAllCaps(false);
        b.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX, dp(16));
        android.graphics.drawable.StateListDrawable states = new android.graphics.drawable.StateListDrawable();
        android.graphics.drawable.GradientDrawable focus = new android.graphics.drawable.GradientDrawable();
        focus.setColor(Color.rgb(233, 239, 241)); focus.setCornerRadius(dp(18));
        android.graphics.drawable.GradientDrawable normal = new android.graphics.drawable.GradientDrawable();
        normal.setColor(Color.rgb(48, 54, 56)); normal.setCornerRadius(dp(18));
        states.addState(new int[]{android.R.attr.state_focused}, focus); states.addState(new int[]{}, normal);
        b.setBackground(states); b.setStateListAnimator(null);
        b.setTextColor(new android.content.res.ColorStateList(
                new int[][]{new int[]{android.R.attr.state_focused},new int[]{}},
                new int[]{Color.rgb(28,32,34),Color.rgb(233,239,241)}));
        b.setPadding(dp(18), dp(8), dp(18), dp(8)); b.setMinHeight(dp(52));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, dp(52)); lp.topMargin = dp(12);
        b.setLayoutParams(lp); return b;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state); item = pending; pending = null;
        if (item == null || !CardListener.isActive(item.getKey())) { finish(); return; }
        Notification n = item.getNotification();
        getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);
        WindowManager.LayoutParams wp = getWindow().getAttributes(); wp.dimAmount = 0.45f;
        wp.gravity = Gravity.RIGHT; wp.width = dp(440); wp.height = -1; getWindow().setAttributes(wp);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(28), dp(36), dp(28), dp(24)); page.setBackgroundColor(Color.rgb(30, 33, 34));
        String app = item.getPackageName();
        try { app = getPackageManager().getApplicationLabel(getPackageManager().getApplicationInfo(app, 0)).toString(); }
        catch (Exception ignored) { }
        page.addView(label(app, 14, Color.LTGRAY));
        LinearLayout text = new LinearLayout(this); text.setOrientation(LinearLayout.VERTICAL);
        text.addView(label(n.extras.getCharSequence(Notification.EXTRA_TITLE), 22, Color.WHITE));
        CharSequence body = n.extras.getCharSequence(Notification.EXTRA_BIG_TEXT);
        if (body == null) body = n.extras.getCharSequence(Notification.EXTRA_TEXT);
        text.addView(label(body, 16, Color.LTGRAY));
        ScrollView scroll = new ScrollView(this); scroll.addView(text);
        page.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        Button first = null;
        if (n.contentIntent != null) {
            Button open = button("Buka");
            open.setOnClickListener(new View.OnClickListener() { public void onClick(View v) {
                if (!CardListener.isActive(item.getKey())) { finish(); return; }
                try { item.getNotification().contentIntent.send(); finish(); }
                catch (PendingIntent.CanceledException ignored) { openUnavailable(); }
            } }); page.addView(open); first = open;
        }
        if (item.isClearable()) {
            Button dismiss = button("Hapus notifikasi");
            dismiss.setOnClickListener(new View.OnClickListener() { public void onClick(View v) {
                CardListener.dismiss(item.getKey()); finish();
            } }); page.addView(dismiss); if (first == null) first = dismiss;
        }
        Button close = button("Tutup");
        close.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { finish(); } });
        page.addView(close); if (first == null) first = close;
        setContentView(page); first.requestFocus();
    }
    private void openUnavailable() {
        android.widget.Toast.makeText(this, "Notifikasi ini sudah tidak tersedia", android.widget.Toast.LENGTH_SHORT).show();
        finish();
    }
    @Override protected void onResume() { super.onResume(); visible = true; CardListener.hideCurrentCard(); }
    @Override protected void onPause() { visible = false; super.onPause(); }
    @Override protected void onDestroy() { item = null; super.onDestroy(); }
}
