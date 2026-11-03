// The tile axis has to take the swipes people actually make.
//
// Reported from a board as "swiping left/right to the other screens is hard".
// Two causes, both pinned here through the real handleTouch():
//
//  * the swipe test was two hard limits -- more than 80 px across AND less than
//    70 px down, inside 0.8 s -- so a thumb's natural arc was thrown away;
//  * on every PAGED screen a drag that started in the outer ring became a rim
//    scroll at touch-down, and a thumb starts almost every swipe near the edge
//    of a 1.75" round panel. The swipe paged the screen instead and was lost.
//
// And the companions that prove the mechanisms still engage: a drag ALONG the
// rim still pages, and a short scrub is still a tap or nothing.
#include "Arduino.h"
#include "Arduino_GFX_Library.h"
#include "Preferences.h"
#include "pet.h"
#include <cstdio>
#include <cmath>
#include <cstring>
#include <chrono>
#include <thread>
uint32_t g_seed=11; FakeSerial Serial; FakeESP ESP; FakeWire Wire;
volatile int g_touchX=0,g_touchY=0; volatile bool g_touchDown=false;
void FakeESP::restart(){exit(0);}
int FakeSerial::available(){return 0;}
String FakeSerial::readStringUntil(char){return String("");}
void setup(); void loop(); void render();
int uiTileIndex(); void uiTileGo(int i);
uint8_t uiCurrentScreen(); uint8_t uiRimPages(); uint8_t uiRimPage();
bool uiIsSwipeH(int dx, int dy, uint32_t dt);
extern const char *const SCREEN_NAME[];
extern uint32_t lastInteract;
extern Pet pet;

static int bad=0;
static void ck(bool ok,const char*w){printf("%s  %s\n",ok?"PASS":"FAIL",w); if(!ok)bad++;}

// handleTouch() gates itself to 50 Hz off millis(), so real time has to pass.
static void pump(int n){ for(int i=0;i<n;i++){ std::this_thread::sleep_for(std::chrono::milliseconds(25)); loop(); } }

// A finger from (x0,y0) to (x1,y1) in `steps` samples, `ms` in total.
static void drag(int x0,int y0,int x1,int y1,int steps,int ms){
  lastInteract = millis();             // awake: a dimmed panel swallows the first gesture
  g_touchX=x0; g_touchY=y0; g_touchDown=true; emuFireInterrupt(); pump(1);
  for (int i=1;i<=steps;i++){
    g_touchX = x0 + (x1-x0)*i/steps; g_touchY = y0 + (y1-y0)*i/steps;
    emuFireInterrupt();
    std::this_thread::sleep_for(std::chrono::milliseconds(ms/steps)); loop();
  }
  g_touchDown=false; emuFireInterrupt(); pump(3);
}
// Along the rim at radius r, from angle a0 to a1 (degrees, screen coordinates).
static void arc(float a0,float a1,int r,int steps){
  lastInteract = millis();
  auto at=[&](float a,int &x,int &y){ x=233+(int)lroundf(r*cosf(a*0.0174533f)); y=233+(int)lroundf(r*sinf(a*0.0174533f)); };
  int x,y; at(a0,x,y);
  g_touchX=x; g_touchY=y; g_touchDown=true; emuFireInterrupt(); pump(1);
  for (int i=1;i<=steps;i++){ at(a0+(a1-a0)*i/steps,x,y); g_touchX=x; g_touchY=y; emuFireInterrupt(); pump(1); }
  g_touchDown=false; emuFireInterrupt(); pump(3);
}

static int findPagedTile(){
  for (int i=0;i<8;i++){ uiTileGo(i); render(); if (uiTileIndex()==i && uiRimPages()>1) return i; }
  return -1;
}

int main(){
  setup();
  for (int i=0;i<4;i++) render();
  if (pet.awaitingStarter()) pet.chooseStarter(0);
  if (pet.isEgg()) pet.dbgHatchAs(1,false);
  pump(4);

  // --- an arc, not a ruler: 130 across and 80 down is a swipe
  {
    int home = 0;
    for (int i=0;i<8;i++){ uiTileGo(i); if (!strcmp(SCREEN_NAME[uiCurrentScreen()],"main")) { home=i; break; } }
    uiTileGo(home); pump(2);
    int before = uiTileIndex();
    drag(160,190, 290,270, 8, 240);     // right-to-left reads as dx>0 here; either way it must MOVE
    ck(uiTileIndex()!=before && uiTileIndex()>=0, "a swipe that drifts 80 px down still moves along the axis");
    ck(uiIsSwipeH(130,80,240) && !uiIsSwipeH(70,90,240), "the dominant axis decides: 130x80 is across, 70x90 is not");
  }
  // --- a slow, deliberate swipe
  {
    uiTileGo(2); pump(2);
    int before = uiTileIndex();
    drag(330,233, 150,240, 12, 1000);
    ck(uiTileIndex()!=before, "a one-second swipe is still a swipe");
  }
  // --- a swipe that STARTS on the rim of a paged screen moves the tile, and
  //     leaves the page where it was
  int paged = findPagedTile();
  ck(paged >= 0, "some tile on the axis pages (the case this guards exists)");
  if (paged >= 0) {
    uiTileGo(paged); pump(2);
    uint8_t page0 = uiRimPage();
    // from the right-hand rim straight across through the middle
    drag(445,233, 200,250, 10, 300);
    int now = uiTileIndex();
    ck(now != paged, "a swipe starting in the outer ring is a swipe, not a scroll");
    uiTileGo(paged); pump(2);
    ck(uiRimPage()==page0, "and the page it crossed on its way out was put back");

    // the companion: following the arc still pages, and does not leave the screen
    uiTileGo(paged); pump(2);
    uint8_t p0 = uiRimPage();
    arc(-30, 30, 212, 12);              // 60 degrees down the right-hand rim
    ck(uiTileIndex()==paged, "a drag along the rim stays on its screen");
    ck(uiRimPage()!=p0, "and it still pages");
  }
  // --- and a scrub is not a swipe
  {
    uiTileGo(2); pump(2);
    int before = uiTileIndex();
    drag(233,300, 263,310, 4, 120);
    ck(uiTileIndex()==before, "a 30 px scrub moves nothing");
  }

  printf("%s\n", bad ? "FAILURES" : "the tile axis takes real swipes");
  return bad ? 1 : 0;
}
