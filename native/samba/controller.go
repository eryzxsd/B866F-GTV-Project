package main

import (
	"context"
	"crypto/rand"
	_ "embed"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"encoding/xml"
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unicode/utf16"

	"golang.org/x/crypto/md4"
)

const module = "/data/adb/modules/ebs_gtv_system_app"
const base = module + "/samba"
const app = "/data/user_de/0/com.local.b866f.launcherpicker"

//go:embed trial.conf
var template string

type config struct {
	Enabled   bool   `json:"enabled"`
	StartBoot bool   `json:"start_boot"`
	ReadOnly  bool   `json:"read_only"`
	Internal  bool   `json:"share_internal"`
	USB       bool   `json:"share_usb"`
	Password  string `json:"password"`
}
type status struct {
	Config    config `json:"config"`
	Running   bool   `json:"running"`
	IP        string `json:"ip"`
	USBCount  int    `json:"usb_count"`
	RequestID string `json:"request_id"`
	Error     string `json:"error"`
	Version   string `json:"version"`
}
type prefs struct {
	Strings []struct {
		Name  string `xml:"name,attr"`
		Value string `xml:",chardata"`
	} `xml:"string"`
	Booleans []struct {
		Name  string `xml:"name,attr"`
		Value string `xml:"value,attr"`
	} `xml:"boolean"`
}

var cfg config
var server *exec.Cmd
var finished chan error
var lastID, lastError string
var lastIP string
var networkPending = errors.New("Jaringan Wi-Fi/Ethernet belum siap")

func save(path string, v any, mode os.FileMode) error {
	b, e := json.Marshal(v)
	if e != nil {
		return e
	}
	old, _ := os.ReadFile(path)
	if string(old) == string(b) {
		return nil
	}
	tmp := path + ".tmp"
	if e = os.WriteFile(tmp, b, mode); e != nil {
		return e
	}
	if e = os.Chmod(tmp, mode); e != nil {
		return e
	}
	if e = os.Rename(tmp, path); e == nil && strings.HasPrefix(path, app+"/") {
		_ = exec.Command("/system/bin/restorecon", "-F", path).Run()
	}
	return e
}
func localNetwork() (string, string, string) {
	ip := ""
	interfaces := []string{"lo"}
	allowed := []string{"127.0.0.1"}
	list, _ := net.Interfaces()
	for _, i := range list {
		if i.Flags&net.FlagUp == 0 || !(strings.HasPrefix(i.Name, "wlan") || strings.HasPrefix(i.Name, "eth")) {
			continue
		}
		addrs, _ := i.Addrs()
		for _, a := range addrs {
			p, n, e := net.ParseCIDR(a.String())
			if e != nil || p.To4() == nil || p.IsLoopback() {
				continue
			}
			if ip == "" {
				ip = p.String()
			}
			interfaces = append(interfaces, i.Name)
			allowed = append(allowed, n.String())
		}
	}
	return ip, strings.Join(interfaces, " "), strings.Join(allowed, " ")
}
func usbCount() int {
	n := 0
	entries, _ := os.ReadDir("/mnt/media_rw")
	for _, e := range entries {
		if e.IsDir() {
			n++
		}
	}
	return n
}
func running() bool {
	return server != nil && server.Process != nil && syscall.Kill(server.Process.Pid, 0) == nil
}
func publish() {
	ip, _, _ := localNetwork()
	_ = save(app+"/files/samba-state.json", status{Config: cfg, Running: running(), IP: ip, USBCount: usbCount(), RequestID: lastID, Error: lastError, Version: "Samba 4.25.0"}, 0644)
}
func cleanupRuntime(sig syscall.Signal) {
	entries, _ := os.ReadDir("/proc")
	for _, entry := range entries {
		pid, e := strconv.Atoi(entry.Name())
		if e != nil || pid <= 1 {
			continue
		}
		path, e := os.Readlink("/proc/" + entry.Name() + "/exe")
		if e != nil {
			continue
		}
		if strings.HasPrefix(path, base+"/runtime/bin/") || strings.HasPrefix(path, base+"/runtime/libexec/samba/") {
			_ = syscall.Kill(pid, sig)
		}
	}
}
func stop() {
	if server != nil {
		pid := server.Process.Pid
		_ = syscall.Kill(-pid, syscall.SIGTERM)
		select {
		case <-finished:
		case <-time.After(3 * time.Second):
			_ = syscall.Kill(-pid, syscall.SIGKILL)
			select {
			case <-finished:
			case <-time.After(time.Second):
			}
		}
		server = nil
		finished = nil
	}
	cleanupRuntime(syscall.SIGTERM)
	time.Sleep(250 * time.Millisecond)
	cleanupRuntime(syscall.SIGKILL)
	fmt.Println("SMB server and owned RPC helpers stopped")
}
func passwordFile() error {
	u := utf16.Encode([]rune(cfg.Password))
	b := make([]byte, 2*len(u))
	for i, v := range u {
		binary.LittleEndian.PutUint16(b[i*2:], v)
	}
	h := md4.New()
	_, _ = h.Write(b)
	record := fmt.Sprintf("shell:2000:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX:%s:[U          ]:LCT-%08X:\n", strings.ToUpper(hex.EncodeToString(h.Sum(nil))), time.Now().Unix())
	path := base + "/private/smbpasswd"
	if e := os.WriteFile(path, []byte(record), 0600); e != nil {
		return e
	}
	return os.Chmod(path, 0600)
}
func render() error {
	ip, interfaces, hosts := localNetwork()
	if ip == "" {
		return networkPending
	}
	lastIP = ip
	s := strings.Replace(template, "interfaces = lo wlan0 eth0", "interfaces = "+interfaces, 1)
	s = strings.Replace(s, "hosts allow = 127.0.0.1 192.168.1.0/24", "hosts allow = "+hosts, 1)
	if !cfg.ReadOnly {
		s = strings.ReplaceAll(s, "read only = yes", "read only = no")
	}
	if !cfg.Internal {
		start := strings.Index(s, "[Shared]")
		end := strings.Index(s, "[USB]")
		s = s[:start] + s[end:]
	}
	if !cfg.USB {
		start := strings.Index(s, "[USB]")
		s = s[:start]
	}
	if e := os.WriteFile(base+"/smb.conf", []byte(s), 0600); e != nil {
		return e
	}
	return passwordFile()
}
func start() error {
	if running() {
		return nil
	}
	if e := render(); e != nil {
		return e
	}
	log, e := os.OpenFile(base+"/log/controller-server.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if e != nil {
		return e
	}
	defer log.Close()
	c := exec.Command(base+"/runtime/bin/smbd", "--foreground", "--no-process-group", "--configfile="+base+"/smb.conf")
	c.Env = append(os.Environ(), "LD_LIBRARY_PATH="+base+"/runtime/lib:"+base+"/runtime/lib/samba", "LD_PRELOAD="+base+"/libb866f_samba_paths.so", "TMPDIR="+base+"/cache")
	c.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	c.Stdin = nil
	c.Stdout = log
	c.Stderr = log
	if e = c.Start(); e != nil {
		return e
	}
	server = c
	finished = make(chan error, 1)
	ch := finished
	go func() { ch <- c.Wait() }()
	select {
	case e := <-finished:
		server = nil
		finished = nil
		return fmt.Errorf("Samba gagal dimulai: %v", e)
	case <-time.After(350 * time.Millisecond):
	}
	fmt.Println("Authenticated SMB server started on local interfaces")
	return nil
}
func readRequest() (string, config, error) {
	c := cfg
	var p prefs
	data, e := os.ReadFile(app + "/shared_prefs/samba_requests.xml")
	if e != nil {
		return "", c, e
	}
	if e = xml.Unmarshal(data, &p); e != nil {
		return "", c, e
	}
	id := ""
	for _, s := range p.Strings {
		if s.Name == "request_id" {
			id = s.Value
		}
		if s.Name == "password" {
			c.Password = s.Value
		}
	}
	for _, v := range p.Booleans {
		if v.Value != "true" && v.Value != "false" {
			return id, c, fmt.Errorf("Nilai opsi tidak valid")
		}
		on := v.Value == "true"
		switch v.Name {
		case "enabled":
			c.Enabled = on
		case "start_boot":
			c.StartBoot = on
		case "read_only":
			c.ReadOnly = on
		case "share_internal":
			c.Internal = on
		case "share_usb":
			c.USB = on
		}
	}
	if len(c.Password) < 8 || len(c.Password) > 64 || strings.ContainsAny(c.Password, "\r\n\x00") {
		return id, c, fmt.Errorf("Kata sandi harus 8–64 karakter")
	}
	if c.Enabled && !c.Internal && !c.USB {
		return id, c, fmt.Errorf("Pilih setidaknya satu folder")
	}
	return id, c, nil
}
func disabled() bool {
	for _, f := range []string{"disable", "remove", "disable_samba"} {
		if _, e := os.Stat(module + "/" + f); e == nil {
			return true
		}
	}
	return false
}
func main() {
	if os.Geteuid() != 0 {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	model, e := exec.CommandContext(ctx, "/system/bin/getprop", "ro.product.model").Output()
	cancel()
	if e != nil || strings.TrimSpace(string(model)) != "B866F V1.1" {
		return
	}
	lock, e := os.OpenFile(base+"/controller.lock", os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return
	}
	defer lock.Close()
	if syscall.Flock(int(lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB) != nil {
		return
	}
	stop()
	cfg = config{ReadOnly: true, Internal: true, USB: true}
	data, e := os.ReadFile(base + "/config.json")
	if e == nil {
		if json.Unmarshal(data, &cfg) != nil {
			return
		}
	}
	if cfg.Password == "" {
		random := make([]byte, 12)
		if _, e = rand.Read(random); e != nil {
			return
		}
		cfg.Password = base64.RawURLEncoding.EncodeToString(random)
	}
	if !cfg.StartBoot {
		cfg.Enabled = false
	}
	_ = save(base+"/config.json", cfg, 0600)
	for _, d := range []string{"private", "state", "cache", "lock", "run", "log", "ncalrpc"} {
		_ = os.MkdirAll(filepath.Join(base, d), 0700)
	}
	if cfg.Enabled {
		if e = start(); e != nil {
			lastError = e.Error()
			if e != networkPending {
				cfg.Enabled = false
				_ = save(base+"/config.json", cfg, 0600)
			}
		}
	}
	defer stop()
	lastID, _, _ = readRequest()
	publish()
	fmt.Println("Samba controls ready")
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, syscall.SIGTERM, syscall.SIGINT)
	fd, e := syscall.InotifyInit1(syscall.IN_CLOEXEC | syscall.IN_NONBLOCK)
	if e != nil {
		return
	}
	defer syscall.Close(fd)
	if _, e = syscall.InotifyAddWatch(fd, app+"/shared_prefs", syscall.IN_CLOSE_WRITE|syscall.IN_MOVED_TO|syscall.IN_CREATE); e != nil {
		return
	}
	buffer := make([]byte, 8192)
	for !disabled() {
		select {
		case <-signals:
			return
		default:
		}
		var reads syscall.FdSet
		reads.Bits[fd/32] |= 1 << uint(fd%32)
		wait := syscall.Timeval{Sec: 5}
		n, e := syscall.Select(fd+1, &reads, nil, nil, &wait)
		if e == syscall.EINTR {
			continue
		}
		if e != nil {
			return
		}
		if n > 0 {
			_, _ = syscall.Read(fd, buffer)
			id, c, e := readRequest()
			if id != "" && id != lastID {
				lastID = id
				lastError = ""
				if e != nil {
					lastError = e.Error()
				} else {
					stop()
					cfg = c
					if e = save(base+"/config.json", cfg, 0600); e != nil {
						lastError = "Gagal menyimpan konfigurasi"
						cfg.Enabled = false
					} else if cfg.Enabled {
						if e = start(); e != nil {
							lastError = e.Error()
							if e != networkPending {
								cfg.Enabled = false
								_ = save(base+"/config.json", cfg, 0600)
							}
						}
					}
				}
				publish()
			}
		} else {
			if server != nil {
				select {
				case <-finished:
					server = nil
					finished = nil
					cfg.Enabled = false
					lastError = "Samba berhenti; silakan aktifkan lagi"
					_ = save(base+"/config.json", cfg, 0600)
				default:
				}
			}
			if cfg.Enabled {
				ip, _, _ := localNetwork()
				if ip != "" && (ip != lastIP || server == nil) {
					stop()
					if e = start(); e != nil {
						lastError = e.Error()
						if e != networkPending {
							cfg.Enabled = false
						}
					} else {
						lastError = ""
					}
				}
			}
			publish()
		}
	}
}
