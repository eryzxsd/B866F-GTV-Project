package com.local.b866f.notificationcards;

import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
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
        nm.notify("b866f_preview", 866, new Notification.Builder(this, ch.getId())
                .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Uji notifikasi B866F")
                .setContentText("Ini contoh kartu notifikasi aplikasi dengan tampilan Google TV.")
                .setOngoing("ongoing".equals(mode)).setTimeoutAfter(10000).build());
        finish();
    }
}
