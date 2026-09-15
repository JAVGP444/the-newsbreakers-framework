#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdint.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static int tnb_try_bind(int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return 0;
    int reuse = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof reuse);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons((uint16_t)port);
    int ok = bind(fd, (struct sockaddr *)&addr, sizeof addr) == 0;
    close(fd);
    return ok;
}

static int tnb_free_port(void) {
    if (tnb_try_bind(8010)) return 8010;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return 8710;
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) != 0) {
        close(fd);
        return 8710;
    }
    socklen_t len = sizeof addr;
    getsockname(fd, (struct sockaddr *)&addr, &len);
    int port = ntohs(addr.sin_port);
    close(fd);
    return port > 0 ? port : 8710;
}

@interface TNBApp : NSObject <NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) WKWebView *web;
@property(nonatomic, strong) NSTextField *status;
@property(nonatomic, strong) NSTask *api;
@property(nonatomic, assign) int port;
@end

@implementation TNBApp

- (NSString *)supportDir {
    return [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/TheNewsBreakers"];
}

- (void)fail:(NSString *)msg {
    NSAlert *a = [[NSAlert alloc] init];
    a.messageText = @"NewsBreakers 2.59.54 a.m.";
    a.informativeText = msg;
    [a runModal];
    [NSApp terminate:nil];
}

- (BOOL)installFromDiskImageIfNeeded {
    NSString *bundle = [[NSBundle mainBundle] bundlePath];
    if (![bundle hasPrefix:@"/Volumes/"]) return NO;
    NSString *dest = [NSHomeDirectory() stringByAppendingPathComponent:@"Desktop/NewsBreakers 2.59.54 a.m..app"];
    [[NSFileManager defaultManager] createDirectoryAtPath:[NSHomeDirectory() stringByAppendingPathComponent:@"Applications"]
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:nil];
    NSTask *copy = [[NSTask alloc] init];
    copy.launchPath = @"/usr/bin/ditto";
    copy.arguments = @[bundle, dest];
    [copy launch];
    [copy waitUntilExit];
    if (copy.terminationStatus != 0) {
        [self fail:@"No pude copiar la app al Escritorio. Arrástrala a Aplicaciones a mano."];
        return YES;
    }
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:dest]];
    [NSApp terminate:nil];
    return YES;
}

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    (void)notification;
    if ([self installFromDiskImageIfNeeded]) return;

    NSMenu *bar = [[NSMenu alloc] init];
    NSMenuItem *appItem = [[NSMenuItem alloc] init];
    [bar addItem:appItem];
    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"NewsBreakers"];
    [appMenu addItemWithTitle:@"Ocultar NewsBreakers" action:@selector(hide:) keyEquivalent:@"h"];
    [appMenu addItemWithTitle:@"Salir de NewsBreakers" action:@selector(terminate:) keyEquivalent:@"q"];
    appItem.submenu = appMenu;

    NSMenuItem *editItem = [[NSMenuItem alloc] init];
    [bar addItem:editItem];
    NSMenu *edit = [[NSMenu alloc] initWithTitle:@"Editar"];
    [edit addItemWithTitle:@"Cortar" action:@selector(cut:) keyEquivalent:@"x"];
    [edit addItemWithTitle:@"Copiar" action:@selector(copy:) keyEquivalent:@"c"];
    [edit addItemWithTitle:@"Pegar" action:@selector(paste:) keyEquivalent:@"v"];
    [edit addItemWithTitle:@"Seleccionar todo" action:@selector(selectAll:) keyEquivalent:@"a"];
    editItem.submenu = edit;
    NSApp.mainMenu = bar;

    NSRect rect = NSMakeRect(0, 0, 1280, 840);
    self.window = [[NSWindow alloc] initWithContentRect:rect
                                              styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                                                         NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    self.window.title = @"NewsBreakers 2.59.54 a.m.";
    self.window.minSize = NSMakeSize(880, 600);
    self.window.delegate = self;
    self.window.backgroundColor = [NSColor colorWithRed:0.024 green:0.051 blue:0.078 alpha:1];
    [self.window center];

    self.status = [[NSTextField alloc] initWithFrame:NSMakeRect(40, 400, 1200, 40)];
    self.status.stringValue = @"Abriendo el observatorio…";
    self.status.bezeled = NO;
    self.status.editable = NO;
    self.status.drawsBackground = NO;
    self.status.alignment = NSTextAlignmentCenter;
    self.status.font = [NSFont systemFontOfSize:18];
    self.status.textColor = [NSColor colorWithWhite:0.85 alpha:1];
    [self.window.contentView addSubview:self.status];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];

    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        [self boot];
    });
}

- (void)boot {
    NSString *setup = [[NSBundle mainBundle] pathForResource:@"setup" ofType:@"sh"];
    if (!setup) {
        dispatch_async(dispatch_get_main_queue(), ^{ [self fail:@"Falta setup.sh dentro de la app."]; });
        return;
    }
    NSTask *prep = [[NSTask alloc] init];
    prep.launchPath = @"/bin/bash";
    prep.arguments = @[setup];
    [prep launch];
    [prep waitUntilExit];
    if (prep.terminationStatus != 0) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [self fail:@"No pude preparar NewsBreakers. Revisa ~/Library/Logs/NewsBreakers.log"];
        });
        return;
    }

    NSString *py = [[self supportDir] stringByAppendingPathComponent:@".venv/bin/python"];
    if (![[NSFileManager defaultManager] isExecutableFileAtPath:py]) {
        dispatch_async(dispatch_get_main_queue(), ^{ [self fail:@"No está Python del entorno. Vuelve a abrir la app."]; });
        return;
    }

    self.port = tnb_free_port();
    NSMutableDictionary *env = [[[NSProcessInfo processInfo] environment] mutableCopy];
    env[@"GATEWAY_PORT"] = [NSString stringWithFormat:@"%d", self.port];
    env[@"GATEWAY_HOST"] = @"127.0.0.1";
    env[@"TNB_SERVE"] = @"1";
    env[@"PYTHONDONTWRITEBYTECODE"] = @"1";

    NSTask *api = [[NSTask alloc] init];
    api.launchPath = py;
    api.arguments = @[@"desktop/app.py", @"--serve"];
    api.currentDirectoryPath = [self supportDir];
    api.environment = env;
    NSString *log = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Logs/NewsBreakers.log"];
    [[NSFileManager defaultManager] createFileAtPath:log contents:nil attributes:nil];
    NSFileHandle *out = [NSFileHandle fileHandleForWritingAtPath:log];
    [out seekToEndOfFile];
    api.standardOutput = out;
    api.standardError = out;
    self.api = api;
    [api launch];

    NSString *health = [NSString stringWithFormat:@"http://127.0.0.1:%d/health", self.port];
    BOOL up = NO;
    for (int i = 0; i < 80; i++) {
        if (![api isRunning]) break;
        NSURL *url = [NSURL URLWithString:health];
        NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url];
        req.timeoutInterval = 1.0;
        dispatch_semaphore_t sem = dispatch_semaphore_create(0);
        __block BOOL ok = NO;
        [[[NSURLSession sharedSession] dataTaskWithRequest:req
                                         completionHandler:^(NSData *d, NSURLResponse *r, NSError *e) {
                                           (void)d;
                                           (void)e;
                                           ok = [(NSHTTPURLResponse *)r statusCode] == 200;
                                           dispatch_semaphore_signal(sem);
                                         }] resume];
        dispatch_semaphore_wait(sem, dispatch_time(DISPATCH_TIME_NOW, 1200 * NSEC_PER_MSEC));
        if (ok) {
            up = YES;
            break;
        }
        [NSThread sleepForTimeInterval:0.25];
    }
    if (!up) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [self fail:@"La API no arrancó. Revisa ~/Library/Logs/NewsBreakers.log"];
        });
        return;
    }

    dispatch_async(dispatch_get_main_queue(), ^{
        [self.status removeFromSuperview];
        WKWebViewConfiguration *conf = [[WKWebViewConfiguration alloc] init];
        WKWebView *web = [[WKWebView alloc] initWithFrame:self.window.contentView.bounds configuration:conf];
        web.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
        web.navigationDelegate = self;
        web.UIDelegate = self;
        self.web = web;
        [self.window.contentView addSubview:web];
        [self.window makeFirstResponder:web];
        NSString *page = [NSString stringWithFormat:@"http://127.0.0.1:%d/?boot=%ld/#/", self.port, (long)time(NULL)];
        NSURLRequest *req = [NSURLRequest requestWithURL:[NSURL URLWithString:page]
                                             cachePolicy:NSURLRequestReloadIgnoringLocalCacheData
                                         timeoutInterval:30];
        [[WKWebsiteDataStore defaultDataStore]
            removeDataOfTypes:[WKWebsiteDataStore allWebsiteDataTypes]
              modifiedSince:[NSDate dateWithTimeIntervalSince1970:0]
            completionHandler:^{
              [web loadRequest:req];
            }];
    });
}

- (BOOL)_isAppURL:(NSURL *)url {
    NSString *host = url.host.lowercaseString;
    return [host isEqualToString:@"127.0.0.1"] || [host isEqualToString:@"localhost"];
}

- (void)webView:(WKWebView *)webView
decidePolicyForNavigationAction:(WKNavigationAction *)action
decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {
    (void)webView;
    NSURL *url = action.request.URL;
    NSString *scheme = url.scheme.lowercaseString;
    BOOL http = [scheme isEqualToString:@"http"] || [scheme isEqualToString:@"https"];
    BOOL newWindow = action.targetFrame == nil;
    BOOL click = action.navigationType == WKNavigationTypeLinkActivated;
    if (url && http && (click || newWindow) && ![self _isAppURL:url]) {
        [[NSWorkspace sharedWorkspace] openURL:url];
        decisionHandler(WKNavigationActionPolicyCancel);
        return;
    }
    decisionHandler(WKNavigationActionPolicyAllow);
}

- (WKWebView *)webView:(WKWebView *)webView
createWebViewWithConfiguration:(WKWebViewConfiguration *)configuration
   forNavigationAction:(WKNavigationAction *)action
        windowFeatures:(WKWindowFeatures *)windowFeatures {
    (void)webView;
    (void)configuration;
    (void)windowFeatures;
    NSURL *url = action.request.URL;
    if (url) [[NSWorkspace sharedWorkspace] openURL:url];
    return nil;
}

- (BOOL)windowShouldClose:(NSWindow *)sender {
    (void)sender;
    [self.api terminate];
    [NSApp terminate:nil];
    return YES;
}

- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    (void)sender;
    if ([self.api isRunning]) [self.api terminate];
    return NSTerminateNow;
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    (void)sender;
    return YES;
}

@end

int main(int argc, const char *argv[]) {
    (void)argc;
    (void)argv;
    @autoreleasepool {
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
        TNBApp *app = [[TNBApp alloc] init];
        NSApp.delegate = app;
        [NSApp run];
    }
    return 0;
}
