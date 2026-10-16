package com.local.b866f.notificationcards;

import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.os.Bundle;

/** A labelled, self-expiring notification to verify the real listener callback. */
public final class PreviewActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        NotificationManager nm = (NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        String mode = getIntent().getStringExtra("mode");
        if ("cleanup".equals(mode) || "cancel".equals(mode)) {
            nm.cancel("b866f_preview", 866);
            if ("cleanup".equals(mode)) {
                nm.deleteNotificationChannel("b866f_preview"); nm.deleteNotificationChannel("b866f_preview_low");
            }
            finish(); return;
        }
        boolean low = "low".equals(mode);
        NotificationChannel ch = new NotificationChannel(low ? "b866f_preview_low" : "b866f_preview", "Uji tampilan", low ? 2 : 4);
        ch.setSound(null, null); ch.enableVibration(false); nm.createNotificationChannel(ch);
        Bundle extras = new Bundle(); extras.putBoolean("b866f_hold_preview", "hold".equals(mode));
        nm.notify("b866f_preview", 866, new Notification.Builder(this, ch.getId()).addExtras(extras)
                .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Uji notifikasi B866F")
                .setContentText("Ini contoh kartu notifikasi aplikasi dengan tampilan Google TV.")
                .setContentIntent(PendingIntent.getActivity(this, 866, new Intent(android.provider.Settings.ACTION_SETTINGS),
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE))
                .setOngoing("ongoing".equals(mode)).setTimeoutAfter("hold".equals(mode) ? 30000 : 10000).build());
        finish();
    }
}
