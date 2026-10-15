package com.local.b866f.launcherpicker;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class LauncherPickerActivity extends Activity {
 private final Handler handler = new Handler();
 private TextView status;
 private LinearLayout list;
 private Context storage;
 private boolean pending;
 private boolean active;
 private String request;
 private int attempts;
 private final int pale=Color.rgb(232,234,237), normal=Color.rgb(224,227,232), dark=Color.rgb(25,29,36);
 private Intent homeIntent() { return new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME); }
 private int dp(float value) { return Math.round(value*getResources().getDisplayMetrics().density); }
 private TextView text(String value,int size) { TextView t=new TextView(this);t.setText(value);t.setTextColor(normal);t.setTextSize(size);return t; }
 private GradientDrawable background(int color) { GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(12));return d; }
 private JSONObject readJson(String name) {
  try { return new JSONObject(new String(Files.readAllBytes(new File(storage.getFilesDir(),name).toPath()),StandardCharsets.UTF_8)); }
  catch(Exception ignored) { return new JSONObject(); }
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  storage=createDeviceProtectedStorageContext();
  active=true;
  // Create the private preferences directory before the local service watches it.
  storage.getSharedPreferences("launcher_requests",MODE_PRIVATE).edit().putBoolean("initialized",true).commit();
  storage.getFilesDir();
  getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,WindowManager.LayoutParams.FLAG_FULLSCREEN);
  getWindow().setGravity(Gravity.RIGHT);
  getWindow().setLayout(Math.round(getResources().getDisplayMetrics().widthPixels*0.50f),WindowManager.LayoutParams.MATCH_PARENT);
  LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.rgb(24,31,42));root.setPadding(dp(30),dp(28),dp(30),dp(20));
  TextView title=text("Ganti launcher",28);title.setTypeface(null,Typeface.NORMAL);root.addView(title);
  status=text("Pilih layar utama. Berlaku saat tombol Home ditekan.",14);status.setPadding(0,dp(12),0,dp(18));root.addView(status);
  ScrollView scroll=new ScrollView(this);scroll.setFillViewport(false);list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);scroll.addView(list);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
  TextView foot=text("Kembali untuk kembali ke Setelan · Tidak menghapus launcher",12);foot.setPadding(0,dp(14),0,0);root.addView(foot);
  setContentView(root);getWindow().setLayout(Math.round(getResources().getDisplayMetrics().widthPixels*0.50f),WindowManager.LayoutParams.MATCH_PARENT);populate();
 }
 private void populate() {
  list.removeAllViews();
  final PackageManager pm=getPackageManager();
  Set<String> managed=new HashSet<>();
  JSONArray disabled=readJson("launcher-state.json").optJSONArray("disabled");
  if(disabled!=null) for(int i=0;i<disabled.length();i++)managed.add(disabled.optString(i));
  ResolveInfo current=pm.resolveActivity(homeIntent(),PackageManager.MATCH_DEFAULT_ONLY);
  String currentPackage=current!=null&&current.activityInfo!=null?current.activityInfo.packageName:"";
  List<ResolveInfo> homes=new ArrayList<>(pm.queryIntentActivities(homeIntent(),PackageManager.MATCH_DEFAULT_ONLY|PackageManager.MATCH_DISABLED_COMPONENTS));
  Collections.sort(homes,new Comparator<ResolveInfo>(){public int compare(ResolveInfo a,ResolveInfo b){return String.valueOf(a.loadLabel(pm)).compareToIgnoreCase(String.valueOf(b.loadLabel(pm)));}});
  Set<String> packages=new HashSet<>(); View focus=null;
  for(ResolveInfo info:homes) {
   ActivityInfo ai=info.activityInfo;if(ai==null||!ai.exported||!ai.applicationInfo.enabled||ai.packageName.equals("com.android.tv.settings"))continue;
   ComponentName cn=new ComponentName(ai.packageName,ai.name);final String component=cn.flattenToString();
   int setting=pm.getComponentEnabledSetting(cn);
   boolean disabledComponent=setting==PackageManager.COMPONENT_ENABLED_STATE_DISABLED||setting==PackageManager.COMPONENT_ENABLED_STATE_DISABLED_USER||(!ai.enabled&&setting!=PackageManager.COMPONENT_ENABLED_STATE_ENABLED);
   if(disabledComponent&&!managed.contains(component))continue;
   if(!packages.add(ai.packageName))continue;
   boolean selected=ai.packageName.equals(currentPackage);
   final LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(14),dp(12),dp(14),dp(12));row.setMinimumHeight(dp(72));row.setFocusable(true);row.setClickable(true);row.setBackground(background(Color.TRANSPARENT));
   ImageView icon=new ImageView(this);icon.setImageDrawable(info.loadIcon(pm));row.addView(icon,new LinearLayout.LayoutParams(dp(38),dp(38)));
   LinearLayout labels=new LinearLayout(this);labels.setOrientation(LinearLayout.VERTICAL);labels.setPadding(dp(14),0,dp(10),0);
   final TextView name=text(ai.packageName.equals("com.google.android.apps.tv.launcherx")?"Google TV":String.valueOf(info.loadLabel(pm)),19);name.setMaxLines(2);labels.addView(name);
   final TextView detail=text(selected?"Default saat ini":ai.packageName,12);detail.setMaxLines(2);detail.setPadding(0,dp(4),0,0);labels.addView(detail);row.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
   final TextView radio=text(selected?"\u25c9":"\u25cb",24);row.addView(radio);
   row.setOnFocusChangeListener(new View.OnFocusChangeListener(){public void onFocusChange(View v,boolean focused){row.setBackground(background(focused?pale:Color.TRANSPARENT));int c=focused?dark:normal;name.setTextColor(c);detail.setTextColor(c);radio.setTextColor(c);}});
   row.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(!pending)select(component);}});
   LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(6);list.addView(row,lp);
   if(focus==null||selected)focus=row;
  }
  if(packages.isEmpty())status.setText("Tidak ada launcher yang tersedia.");
  if(focus!=null)focus.requestFocus();
 }
 private void select(String component) {
  pending=true;attempts=0;request=Long.toString(System.nanoTime());status.setText("Menerapkan pilihan…");
  SharedPreferences prefs=storage.getSharedPreferences("launcher_requests",MODE_PRIVATE);
  if(!prefs.edit().putString("launcher_component",component).putString("request_id",request).commit()){pending=false;status.setText("Gagal menyimpan pilihan.");return;}
  handler.postDelayed(checkResult,250);
 }
 private final Runnable checkResult=new Runnable(){public void run(){
  if(!active)return;
  JSONObject response=readJson("launcher-result.json");
  if(request.equals(response.optString("request_id"))){
   pending=false;populate();
   if(response.optBoolean("ok")){
    boolean warning=response.optBoolean("cleanup_warning");
    status.setText(warning?"Launcher tersimpan; launcher lama belum berhasil dihentikan.":"Launcher tersimpan. Tekan Home untuk membukanya.");
    Toast.makeText(LauncherPickerActivity.this,warning?"Launcher diganti; penghentian launcher lama gagal.":"Launcher berhasil diganti dengan akses root.",Toast.LENGTH_LONG).show();
   }else{status.setText("Pilihan gagal diterapkan. Launcher sebelumnya dipulihkan.");}
   return;
  }
  if(++attempts>=80){pending=false;status.setText("Layanan belum merespons. Pilihan belum terverifikasi.");return;}
  handler.postDelayed(this,250);
 }};
 @Override public void onResume(){super.onResume();if(list!=null&&!pending)populate();}
 @Override public boolean onKeyDown(int keyCode,android.view.KeyEvent event){if(keyCode==android.view.KeyEvent.KEYCODE_DPAD_LEFT){finish();return true;}return super.onKeyDown(keyCode,event);}
 @Override public void onDestroy(){active=false;handler.removeCallbacks(checkResult);super.onDestroy();}
}
