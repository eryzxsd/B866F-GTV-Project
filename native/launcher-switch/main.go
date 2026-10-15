package main

import (
 "context"
 "encoding/json"
 "encoding/xml"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strings"
 "syscall"
 "time"
)

const module = "/data/adb/modules/ebs_gtv_system_app"
const appDir = "/data/user_de/0/com.local.b866f.launcherpicker"
const prefsDir = appDir + "/shared_prefs"
const prefsFile = prefsDir + "/launcher_requests.xml"
var componentPattern = regexp.MustCompile(`^[A-Za-z0-9_.$]+/[A-Za-z0-9_.$]+$`)
type state struct { Disabled []string `json:"disabled"` }
type request struct { ID string; Component string }
type result struct {
 ID string `json:"request_id"`
 OK bool `json:"ok"`
 PreviousStopped string `json:"previous_stopped,omitempty"`
 CleanupWarning bool `json:"cleanup_warning,omitempty"`
}
type preferences struct { Strings []struct { Name string `xml:"name,attr"`; Value string `xml:",chardata"` } `xml:"string"` }

func run(binary string,args ...string)(string,error){ctx,cancel:=context.WithTimeout(context.Background(),8*time.Second);defer cancel();b,e:=exec.CommandContext(ctx,"/system/bin/"+binary,args...).CombinedOutput();return strings.TrimSpace(string(b)),e}
func cmd(args ...string)(string,error){return run("cmd",args...)}
func canonical(component string)string{parts:=strings.SplitN(component,"/",2);if len(parts)!=2{return ""};if strings.HasPrefix(parts[1],"."){parts[1]=parts[0]+parts[1]};return strings.Join(parts,"/")}
func pkg(component string)string{return strings.SplitN(component,"/",2)[0]}
func contains(list []string,value string)bool{for _,x:=range list{if x==value{return true}};return false}
func save(path string,value any)error{data,e:=json.Marshal(value);if e!=nil{return e};tmp:=path+".tmp";if e=os.WriteFile(tmp,data,0644);e!=nil{return e};if e=os.Rename(tmp,path);e==nil{_,_=run("restorecon","-F",path)};return e}
func readRequest()(request,error){var r request;b,e:=os.ReadFile(prefsFile);if e!=nil{return r,e};var p preferences;if e=xml.Unmarshal(b,&p);e!=nil{return r,e};for _,s:=range p.Strings{if s.Name=="request_id"{r.ID=s.Value};if s.Name=="launcher_component"{r.Component=canonical(s.Value)}};return r,nil}
func homes()([]string,error){out,e:=cmd("package","query-activities","--components","--query-flags","65536","--user","0","-a","android.intent.action.MAIN","-c","android.intent.category.HOME");if e!=nil{return nil,e};var list []string;for _,line:=range strings.Split(out,"\n"){line=strings.TrimSpace(line);if componentPattern.MatchString(line)&&!strings.HasPrefix(line,"com.android.tv.settings/"){list=append(list,canonical(line))}};return list,nil}
func current()string{out,e:=cmd("package","resolve-activity","--brief","--user","0","-a","android.intent.action.MAIN","-c","android.intent.category.HOME");if e!=nil{return ""};for _,line:=range strings.Split(out,"\n"){line=strings.TrimSpace(line);if componentPattern.MatchString(line){return canonical(line)}};return ""}
func enabled(component string,on bool)bool{action:="disable";if on{action="enable"};out,e:=cmd("package",action,"--user","0",component);if e!=nil{fmt.Println("Home component change failed:",out,e)};return e==nil}
func setHome(component string)bool{out,e:=cmd("package","set-home-activity","--user","0",component);return e==nil&&strings.Contains(out,"Success")}
func loadState()state{var s state;b,e:=os.ReadFile(module+"/launcher-managed-components.json");if e==nil{_ = json.Unmarshal(b,&s)};return s}
func persist(s state) { _=save(module+"/launcher-managed-components.json",s);_=save(appDir+"/files/launcher-state.json",s) }

func apply(r request)result{
 outcome:=result{ID:r.ID}
 if r.ID==""||len(r.ID)>64||!componentPattern.MatchString(r.Component){return outcome}
 old:=loadState();available,e:=homes();if e!=nil{return outcome}
 if !contains(available,r.Component)&&!contains(old.Disabled,r.Component){fmt.Println("Rejected target outside enabled/locally-managed Home activities");return outcome}
 previous:=current();if previous==""{return outcome}
 // Restore only components this helper previously disabled. Entire apps remain installed/enabled.
 for _,c:=range old.Disabled{if componentPattern.MatchString(c){_=enabled(c,true)}}
 now:=state{Disabled:[]string{}}
 rollback:=func(){for _,c:=range now.Disabled{_=enabled(c,true)};for _,c:=range old.Disabled{_=enabled(c,false)};_=setHome(previous);persist(old)}
 if !setHome(r.Component){rollback();return outcome}
 // This firmware prioritizes Google Home over the selected role holder. Disable
 // only conflicting HOME entry points, recording each so selection can reverse it.
 for tries:=0;tries<=len(available)+len(old.Disabled)+1;tries++{
  actual:=current()
  if actual!=""&&pkg(actual)==pkg(r.Component){
   persist(now)
   outcome.OK=true
   fmt.Println("Verified launcher selection:",pkg(r.Component))
   // Stop only the previous default, and only after the new default is verified.
   // Re-selecting the current launcher never force-stops it.
   if pkg(previous)!=pkg(actual) && contains(available,previous) {
    output,err:=run("am","force-stop","--user","0",pkg(previous))
    if err!=nil { outcome.CleanupWarning=true;fmt.Println("Previous launcher force-stop failed:",output,err) } else { outcome.PreviousStopped=pkg(previous);fmt.Println("Previous launcher force-stopped:",pkg(previous)) }
   }
   return outcome
  }
  if actual==""||strings.HasPrefix(actual,"com.android.tv.settings/")||!componentPattern.MatchString(actual)||contains(now.Disabled,actual){rollback();return outcome}
  now.Disabled=append(now.Disabled,actual)
  // Journal before changing the component, so interruption leaves a restoration record.
  persist(now)
  if !enabled(actual,false)||!setHome(r.Component){rollback();return outcome}
 }
 rollback();return outcome
}
func disabled()bool{for _,name:=range []string{"disable","remove","disable_launcher_switch"}{if _,e:=os.Stat(filepath.Join(module,name));e==nil{return true}};return false}
func main(){
 if os.Geteuid()!=0{return};model,e:=run("getprop","ro.product.model");if e!=nil||model!="B866F V1.1"{return}
 lock,e:=os.OpenFile(module+"/launcher-switch.lock",os.O_CREATE|os.O_RDWR,0600);if e!=nil{return};defer lock.Close();if syscall.Flock(int(lock.Fd()),syscall.LOCK_EX|syscall.LOCK_NB)!=nil{return}
 fd,e:=syscall.InotifyInit1(syscall.IN_CLOEXEC|syscall.IN_NONBLOCK);if e!=nil{return};defer syscall.Close(fd)
 if _,e=syscall.InotifyAddWatch(fd,prefsDir,syscall.IN_CLOSE_WRITE|syscall.IN_MOVED_TO|syscall.IN_CREATE);e!=nil{fmt.Println(e);return}
 persist(loadState());last,_:=readRequest();seen:=last.ID;fmt.Println("Dynamic launcher picker ready; existing default retained")
 buffer:=make([]byte,8192)
 for !disabled(){var reads syscall.FdSet;reads.Bits[fd/32]|=1<<uint(fd%32);wait:=syscall.Timeval{Sec:5};n,e:=syscall.Select(fd+1,&reads,nil,nil,&wait);if e==syscall.EINTR{continue};if e!=nil{return};if n==0{continue};_,_=syscall.Read(fd,buffer);if disabled(){return};r,e:=readRequest();if e!=nil||r.ID==""||r.ID==seen{continue};seen=r.ID;outcome:=apply(r);_=save(appDir+"/files/launcher-result.json",outcome);if !outcome.OK{fmt.Println("Launcher choice failed; rollback attempted")}}
}
