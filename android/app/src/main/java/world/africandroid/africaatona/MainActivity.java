package world.africandroid.africaatona;
import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.*;
import android.widget.Toast;
import android.widget.EditText;
public class MainActivity extends Activity {
 private WebView web;
 private GeolocationPermissions.Callback pending;
 private String pendingOrigin;
 private final String home="https://africaatona.africandroid.world/";
 private boolean trusted(Uri u){return "https".equals(u.getScheme())&&"africaatona.africandroid.world".equals(u.getHost())&&(u.getPort()==-1||u.getPort()==443);}
 @Override public void onCreate(Bundle b){
  super.onCreate(b);web=new WebView(this);setContentView(web);
  web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);
  web.getSettings().setGeolocationEnabled(true);web.getSettings().setAllowFileAccess(false);
  web.getSettings().setAllowContentAccess(false);web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
  web.setWebViewClient(new WebViewClient(){
   @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){
    Uri u=r.getUrl();if(trusted(u))return false;
    if(r.isForMainFrame()&&("https".equals(u.getScheme())||"mailto".equals(u.getScheme())))try{startActivity(new Intent(Intent.ACTION_VIEW,u));}catch(Exception e){Toast.makeText(MainActivity.this,"No app can open this link",Toast.LENGTH_LONG).show();}
    return true;
   }
   @Override public void onReceivedError(WebView v,WebResourceRequest r,WebResourceError e){if(r.isForMainFrame())new AlertDialog.Builder(MainActivity.this).setTitle("Unable to connect").setMessage("Check your connection. AFRICA ATONA requires its hosted service.").setPositiveButton("Retry",(d,w)->web.loadUrl(home)).setNegativeButton("Close",null).show();}
  });
  web.setWebChromeClient(new WebChromeClient(){
   @Override public boolean onJsAlert(WebView v,String url,String message,JsResult result){
    new AlertDialog.Builder(MainActivity.this).setMessage(message).setPositiveButton("OK",(d,w)->result.confirm()).setOnCancelListener(d->result.cancel()).show();return true;
   }
   @Override public boolean onJsConfirm(WebView v,String url,String message,JsResult result){
    new AlertDialog.Builder(MainActivity.this).setMessage(message).setPositiveButton("Confirm",(d,w)->result.confirm()).setNegativeButton("Cancel",(d,w)->result.cancel()).setOnCancelListener(d->result.cancel()).show();return true;
   }
   @Override public boolean onJsPrompt(WebView v,String url,String message,String value,JsPromptResult result){
    EditText input=new EditText(MainActivity.this);input.setText(value);
    new AlertDialog.Builder(MainActivity.this).setMessage(message).setView(input).setPositiveButton("Save",(d,w)->result.confirm(input.getText().toString())).setNegativeButton("Cancel",(d,w)->result.cancel()).setOnCancelListener(d->result.cancel()).show();return true;
   }
   @Override public void onGeolocationPermissionsShowPrompt(String origin,GeolocationPermissions.Callback callback){
    if(!trusted(Uri.parse(origin))){callback.invoke(origin,false,false);return;}
    if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED||checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED){callback.invoke(origin,true,false);return;}
    pending=callback;pendingOrigin=origin;requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},7);
   }
  });
  web.setDownloadListener((url,agent,disposition,mime,length)->{Uri u=Uri.parse(url);if(trusted(u))startActivity(new Intent(Intent.ACTION_VIEW,u));});
  web.loadUrl(home);
 }
 @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] results){super.onRequestPermissionsResult(code,permissions,results);if(code==7&&pending!=null){boolean allowed=false;for(int r:results)if(r==PackageManager.PERMISSION_GRANTED)allowed=true;pending.invoke(pendingOrigin,allowed,false);pending=null;}}
 @Override public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
 @Override protected void onPause(){super.onPause();web.onPause();web.evaluateJavascript("if(typeof stopNav==='function')stopNav()",null);}
 @Override protected void onResume(){super.onResume();if(web!=null)web.onResume();}
 @Override protected void onDestroy(){if(web!=null)web.destroy();super.onDestroy();}
}
