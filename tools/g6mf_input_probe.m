#import <AppKit/AppKit.h>
#import <QuartzCore/QuartzCore.h>
#include <sys/sysctl.h>
static uint64_t copies(void){uint64_t v=0;size_t n=sizeof v;sysctlbyname("debug.nvaccel_iop_ok_h4",&v,&n,NULL,0);return v;}
static NSDictionary *summary(NSArray<NSNumber*> *values){
 NSArray *v=[values sortedArrayUsingSelector:@selector(compare:)];if(!v.count)return @{@"count":@0};
 return @{@"count":@(v.count),@"min_ms":v[0],@"p50_ms":v[(v.count-1)/2],@"p95_ms":v[(NSUInteger)ceil(v.count*0.95)-1],@"max_ms":v.lastObject};
}
@interface InputView:NSView
@property NSMutableArray<NSNumber*> *delivery;
@property double latestTimestamp;
@property NSPoint latestPoint;
@property BOOL pending;
@property NSUInteger invalid;
@property NSTrackingArea *tracking;
@end
@implementation InputView
-(void)updateTrackingAreas{[super updateTrackingAreas];if(self.tracking)[self removeTrackingArea:self.tracking];self.tracking=[[NSTrackingArea alloc]initWithRect:NSZeroRect options:NSTrackingMouseMoved|NSTrackingActiveAlways|NSTrackingInVisibleRect owner:self userInfo:nil];[self addTrackingArea:self.tracking];}
-(void)mouseMoved:(NSEvent*)event{
 double ms=(CACurrentMediaTime()-event.timestamp)*1000;
 if(ms<0||ms>10000){self.invalid++;return;}
 if(self.delivery.count<20000)[self.delivery addObject:@(ms)];
 self.latestTimestamp=event.timestamp;self.latestPoint=[self convertPoint:event.locationInWindow fromView:nil];self.pending=YES;
}
-(void)mouseDragged:(NSEvent*)event{[self mouseMoved:event];}
@end
@interface InputProbe:NSObject
@property NSWindow *window;
@property InputView *view;
@property CALayer *marker;
@property CADisplayLink *link;
@property NSMutableArray<NSNumber*> *commitDelays,*tickGaps;
@property double lastTick,started;
@property uint64_t initialCopies;
@property NSString *output;
@property BOOL done;
@end
@implementation InputProbe
-(void)tick:(CADisplayLink*)link{
 double now=CACurrentMediaTime();if(self.lastTick&&self.tickGaps.count<10000)[self.tickGaps addObject:@((now-self.lastTick)*1000)];self.lastTick=now;
 if(self.view.pending){
  [CATransaction begin];[CATransaction setDisableActions:YES];self.marker.position=CGPointMake(self.view.latestPoint.x,self.view.latestPoint.y);[CATransaction commit];
  if(self.commitDelays.count<20000)[self.commitDelays addObject:@((CACurrentMediaTime()-self.view.latestTimestamp)*1000)];self.view.pending=NO;
 }
}
-(void)finish{
 if(self.done)return;self.done=YES;[self.link invalidate];double seconds=CACurrentMediaTime()-self.started;
 NSDictionary *result=@{@"event_to_app":summary(self.view.delivery),@"event_to_layer_commit":summary(self.commitDelays),@"display_link_intervals":summary(self.tickGaps),@"invalid_timestamp_events":@(self.view.invalid),@"seconds":@(seconds),@"panel_copies_per_second":@((copies()-self.initialCopies)/seconds),@"sufficient_events":@(self.view.delivery.count>=30),@"note":@"Measures delivery to this application and layer commit, not physical input-to-photon latency. Latest event per display-link callback is used for commit timing."};
 NSData *json=[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted|NSJSONWritingSortedKeys error:nil];
 NSError *error=nil;if(![json writeToFile:self.output options:NSDataWritingAtomic error:&error])fprintf(stderr,"write failed: %s\n",error.description.UTF8String);
 printf("%s\n",[[[NSString alloc]initWithData:json encoding:NSUTF8StringEncoding]UTF8String]);fflush(stdout);[self.window orderOut:nil];[NSApp terminate:nil];
}
@end
int main(int argc,char **argv){@autoreleasepool{
 if(argc==2&&!strcmp(argv[1],"--self-test")){
  NSDictionary *s=summary(@[@1,@2,@3,@4,@5,@6,@7,@8,@9,@10,@11,@12,@13,@14,@15,@16,@17,@18,@19,@20]);
  if([s[@"count"]intValue]!=20||[s[@"p50_ms"]intValue]!=10||[s[@"p95_ms"]intValue]!=19||[summary(@[])[@"count"]intValue]!=0)return 2;
  puts("INPUT STATS PASS: empty set and percentile boundaries");return 0;
 }
 if(argc!=2||getuid()==0){fprintf(stderr,"Run as your ordinary user: input-probe output.json\n");return 1;}
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];[NSApp finishLaunching];
 InputProbe *p=[InputProbe new];p.output=[NSString stringWithUTF8String:argv[1]];p.commitDelays=[NSMutableArray new];p.tickGaps=[NSMutableArray new];
 p.window=[[NSPanel alloc]initWithContentRect:NSMakeRect(120,120,900,560) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskNonactivatingPanel backing:NSBackingStoreBuffered defer:NO];p.window.title=@"G6MF — двигай мышью внутри окна 20 секунд";p.window.releasedWhenClosed=NO;p.window.acceptsMouseMovedEvents=YES;
 p.view=[[InputView alloc]initWithFrame:NSMakeRect(0,0,900,560)];p.view.delivery=[NSMutableArray new];p.view.wantsLayer=YES;p.view.layer.backgroundColor=NSColor.darkGrayColor.CGColor;p.window.contentView=p.view;
 NSTextField *label=[NSTextField labelWithString:@"Двигай мышью внутри этого окна. Синий круг следует за событиями.\nОкно закроется само через 20 секунд."];label.frame=NSMakeRect(24,480,850,50);label.textColor=NSColor.whiteColor;[p.view addSubview:label];
 p.marker=[CALayer layer];p.marker.bounds=CGRectMake(0,0,24,24);p.marker.cornerRadius=12;p.marker.backgroundColor=NSColor.systemBlueColor.CGColor;[p.view.layer addSublayer:p.marker];
 [p.window orderFrontRegardless];p.started=CACurrentMediaTime();p.initialCopies=copies();p.link=[p.view displayLinkWithTarget:p selector:@selector(tick:)];p.link.preferredFrameRateRange=CAFrameRateRangeMake(30,165,165);[p.link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
 double duration=getenv("G6MF_INPUT_SECONDS")?atof(getenv("G6MF_INPUT_SECONDS")):20;duration=fmax(2,fmin(60,duration));
 [NSTimer scheduledTimerWithTimeInterval:duration repeats:NO block:^(NSTimer *timer){[p finish];}];[NSApp run];return 0;
}}
