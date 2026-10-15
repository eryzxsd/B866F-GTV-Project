package com.local.b866f.launcherpicker;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public final class SambaSettingsActivity extends Activity {
 private Context storage;
 private final Handler handler=new Handler();
 private LinearLayout rows;
 private TextView status;
 private JSONObject state=new JSONObject(),config=new JSONObject();
 private boolean resumed,pending;
 private String request="",lastRaw="";
 private int attempts;
 private final int pale=Color.rgb(232,234,237),normal=Color.rgb(224,227,232),dark=Color.rgb(25,29,36);
 private int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
 private TextView text(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(normal);return t;}
 private GradientDrawable shape(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}
 @Override public void onCreate(Bundle saved){super.onCreate(saved);storage=createDeviceProtectedStorageContext();storage.getSharedPreferences("samba_requests",MODE_PRIVATE).edit().putBoolean("initialized",true).commit();storage.getFilesDir();getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,WindowManager.LayoutParams.FLAG_FULLSCREEN);getWindow().setGravity(Gravity.RIGHT);
  LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(30),dp(28),dp(30),dp(14));root.setBackgroundColor(Color.rgb(24,31,42));root.addView(text("Samba server",28));status=text("Memuat layanan lokal…",14);status.setPadding(0,dp(10),0,dp(12));root.addView(status);ScrollView scroll=new ScrollView(this);rows=new LinearLayout(this);rows.setOrientation(LinearLayout.VERTICAL);scroll.addView(rows);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));TextView foot=text("SMB2/3 · Login wajib · Jaringan lokal",12);foot.setPadding(0,dp(10),0,0);root.addView(foot);setContentView(root);getWindow().setLayout(Math.round(getResources().getDisplayMetrics().widthPixels*0.50f),-1);
 }
 private void toggle(final String key,String title,String summary){row(key,title,summary,true,config.optBoolean(key),new Runnable(){public void run(){try{config.put(key,!config.optBoolean(key));send();}catch(Exception ignored){}}});}
 private void row(final String key,String title,String summary,boolean toggle,boolean checked,final Runnable action){
  final LinearLayout row=new LinearLayout(this);row.setTag(key);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(12),dp(10),dp(12),dp(10));row.setMinimumHeight(dp(64));row.setFocusable(true);row.setClickable(true);row.setBackground(shape(Color.TRANSPARENT,12));
  LinearLayout labels=new LinearLayout(this);labels.setOrientation(LinearLayout.VERTICAL);final TextView name=text(title,18);name.setMaxLines(2);labels.addView(name);final TextView detail=text(summary,12);detail.setPadding(0,dp(4),dp(10),0);detail.setMaxLines(3);labels.addView(detail);row.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
  if(toggle){FrameLayout track=new FrameLayout(this);GradientDrawable bg=shape(checked?Color.rgb(174,203,250):Color.rgb(65,74,87),20);if(!checked)bg.setStroke(dp(1),Color.rgb(141,150,166));track.setBackground(bg);View thumb=new View(this);thumb.setBackground(shape(checked?Color.rgb(23,52,92):Color.rgb(203,208,217),20));int size=checked?18:14;FrameLayout.LayoutParams tp=new FrameLayout.LayoutParams(dp(size),dp(size),Gravity.CENTER_VERTICAL|Gravity.LEFT);tp.leftMargin=dp(checked?21:4);track.addView(thumb,tp);row.addView(track,new LinearLayout.LayoutParams(dp(42),dp(24)));}
  row.setOnFocusChangeListener(new View.OnFocusChangeListener(){public void onFocusChange(View v,boolean focus){row.setBackground(shape(focus?pale:Color.TRANSPARENT,12));name.setTextColor(focus?dark:normal);detail.setTextColor(focus?dark:normal);}});
  row.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(!pending)action.run();}});LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(4);rows.addView(row,lp);
 }
 private void render(){String focus="enabled";View previous=getCurrentFocus();if(previous!=null&&previous.getTag() instanceof String)focus=(String)previous.getTag();rows.removeAllViews();
  toggle("enabled","Aktifkan Samba server","Shared dan USB melalui jaringan lokal");
  toggle("share_internal","Bagikan folder Shared","Penyimpanan internal / Shared");
  toggle("share_usb","Bagikan USB",state.optInt("usb_count")==0?"Belum ada USB terpasang":"Drive terpasang: "+state.optInt("usb_count"));
  row("write","Izinkan menulis",config.optBoolean("read_only")?"Nonaktif: hanya membaca file":"Aktif: perangkat yang login dapat mengubah file",true,!config.optBoolean("read_only"),new Runnable(){public void run(){try{config.put("read_only",!config.optBoolean("read_only"));send();}catch(Exception ignored){}}});
  toggle("start_boot","Mulai saat boot","Mengikuti pilihan aktif/nonaktif terakhir");
  row("password","Ubah kata sandi","Minimal 8 karakter; akun: shell",false,false,new Runnable(){public void run(){passwordDialog();}});
  row("connect","Cara menghubungkan","Alamat, akun, dan kata sandi",false,false,new Runnable(){public void run(){connectionDialog();}});
  for(int i=0;i<rows.getChildCount();i++)if(focus.equals(rows.getChildAt(i).getTag()))rows.getChildAt(i).requestFocus();
 }
 private void passwordDialog(){final EditText input=new EditText(this);input.setSingleLine(true);input.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);input.setHint("Kata sandi baru");final AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Ubah kata sandi Samba").setView(input).setNegativeButton("Batal",null).setPositiveButton("Simpan",null).create();dialog.setOnShowListener(new android.content.DialogInterface.OnShowListener(){public void onShow(android.content.DialogInterface d){dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(new View.OnClickListener(){public void onClick(View v){String value=input.getText().toString();if(value.length()<8||value.length()>64||value.indexOf('\n')>=0||value.indexOf('\r')>=0){input.setError("Gunakan 8–64 karakter");return;}try{config.put("password",value);dialog.dismiss();send();}catch(Exception ignored){}}});}});dialog.show();}
 private void connectionDialog(){String ip=state.optString("ip","");String message="Aktifkan server, lalu buka alamat berikut di laptop:\n\n";if(config.optBoolean("share_internal"))message+="\\\\"+ip+"\\Shared\n";if(config.optBoolean("share_usb"))message+="\\\\"+ip+"\\USB\n";message+="\nAkun: shell\nKata sandi: "+config.optString("password")+"\n\nUSB menampilkan drive yang terpasang. Perubahan opsi dapat memulai ulang server.";new AlertDialog.Builder(this).setTitle("Akses Samba").setMessage(message).setPositiveButton("Tutup",null).show();}
 private void send(){request=Long.toString(System.nanoTime());SharedPreferences.Editor edit=storage.getSharedPreferences("samba_requests",MODE_PRIVATE).edit().putString("request_id",request).putString("password",config.optString("password"));for(String key:new String[]{"enabled","start_boot","read_only","share_internal","share_usb"})edit.putBoolean(key,config.optBoolean(key));if(!edit.commit()){status.setText("Gagal menyimpan pilihan.");return;}pending=true;attempts=0;status.setText("Menerapkan pengaturan…");}
 private final Runnable poll=new Runnable(){public void run(){if(!resumed)return;try{String raw=new String(Files.readAllBytes(new File(storage.getFilesDir(),"samba-state.json").toPath()),StandardCharsets.UTF_8);JSONObject next=new JSONObject(raw);if(!pending||request.equals(next.optString("request_id"))){if(!raw.equals(lastRaw)){state=next;config=state.getJSONObject("config");lastRaw=raw;render();}if(pending){pending=false;String error=next.optString("error");if(!error.isEmpty())Toast.makeText(SambaSettingsActivity.this,error,Toast.LENGTH_LONG).show();}String error=state.optString("error");status.setText(!error.isEmpty()?error:state.optBoolean("running")?"Aktif · "+state.optString("ip")+" · Samba 4.25.0":"Nonaktif · Tidak ada server jaringan yang berjalan");}}catch(Exception ignored){if(!pending)status.setText("Menunggu layanan Samba lokal…");}if(pending&&++attempts>=30){pending=false;status.setText("Layanan belum merespons. Pilihan belum terverifikasi.");}handler.postDelayed(this,800);}};
 @Override public void onResume(){super.onResume();resumed=true;handler.removeCallbacks(poll);handler.post(poll);}
 @Override public void onPause(){resumed=false;handler.removeCallbacks(poll);super.onPause();}
 @Override public boolean onKeyDown(int keyCode,android.view.KeyEvent event){if(keyCode==android.view.KeyEvent.KEYCODE_DPAD_LEFT){finish();return true;}return super.onKeyDown(keyCode,event);}
}
