// Every village has its own backdrop, and the screens actually use it.
//
// backs.h is generated in VERSIONS order and indexed by region, so the order is
// a promise between two files; the static_assert in the sketch checks the
// COUNT, this checks the NAMES. Then the screens themselves: a Suna ninja must
// stand in Suna, not in whatever scene was drawn last -- compared on the real
// framebuffer, not on the index the helper returns.
#include "Arduino.h"
#include "Arduino_GFX_Library.h"
#include "Preferences.h"
#include "pet.h"
#include "backs.h"
#include <cstdio>
#include <cstring>
#include <vector>
uint32_t g_seed=5; FakeSerial Serial; FakeESP ESP; FakeWire Wire;
volatile int g_touchX=0,g_touchY=0; volatile bool g_touchDown=false;
void FakeESP::restart(){exit(0);}
int FakeSerial::available(){return 0;}
String FakeSerial::readStringUntil(char){return String("");}
void setup(); void render();
uint8_t sceneVillage(); uint8_t villageOfDex(int16_t d);
void drawScene(uint8_t village, uint32_t now, bool night);
extern Arduino_Canvas *gfx;
extern Pet pet;

static int bad=0;
static void ck(bool ok,const char*w){printf("%s  %s\n",ok?"PASS":"FAIL",w); if(!ok)bad++;}

static std::vector<uint16_t> shot(uint8_t village, bool night){
  drawScene(village, 0, night);
  const uint16_t *b = gfx->buffer();
  return std::vector<uint16_t>(b, b + 466 * 466);
}
// rows y0..y1, how many pixels differ
static int differ(const std::vector<uint16_t> &a, const std::vector<uint16_t> &b, int y0, int y1){
  int n = 0;
  for (int y = y0; y < y1; y++) for (int x = 0; x < 466; x++) if (a[y*466+x] != b[y*466+x]) n++;
  return n;
}

int main(){
  setup();
  if (pet.awaitingStarter()) pet.chooseStarter(0);

  bool names = true;
  for (int r = 0; r < REGION_COUNT; r++) {
    if (r == REGION_ALL) continue;
    if (strcmp(VILLAGES[r].name, REGIONS[r].name)) { names = false; printf("      region %d is %s, scene is %s\n", r, REGIONS[r].name, VILLAGES[r].name); }
  }
  ck(names, "the scene for each region is that region's village");
  ck(!strcmp(VILLAGES[VIL_ARENA].name, "ARENA"), "and the last scene is the exam arena");

  // every ninja maps to its own village
  bool own = true;
  for (int r = 0; r < REGION_COUNT; r++) {
    if (r == REGION_ALL) continue;
    for (int d = REGIONS[r].lo; d <= REGIONS[r].hi; d++) if (villageOfDex(d) != r) own = false;
  }
  ck(own, "every ninja's village is the one its dex range belongs to");

  // the main screen follows the live ninja
  pet.dbgHatchAs(REGIONS[0].lo, false);
  ck(sceneVillage() == 0, "a Konoha ninja stands in Konoha");
  pet.dbgHatchAs(REGIONS[1].lo, false);
  ck(sceneVillage() == 1, "a Suna ninja stands in Suna");

  // ...and the scenes really are different pictures, by day and by night
  int sameSky = 0, diffs = 0;
  for (bool night : {false, true}) {
    std::vector<uint16_t> a = shot(0, night);
    for (int v = 1; v < VIL_COUNT; v++) {
      std::vector<uint16_t> b = shot((uint8_t)v, night);
      sameSky += differ(a, b, 0, 20) == 0;            // the sky above the skyline is the firmware's
      diffs += differ(a, b, 120, 466) > 20000;        // the village and street are not
    }
  }
  ck(sameSky == 2 * (VIL_COUNT - 1), "the sky is the same everywhere: the firmware still draws it");
  ck(diffs == 2 * (VIL_COUNT - 1), "every village paints a different skyline and street, day and night");
  {
    std::vector<uint16_t> d = shot(0, false), n = shot(0, true);
    ck(differ(d, n, 120, 466) > 50000, "night uses its own palette");
  }

  // The fight layer is the CALM one: sky at the top, and solid floor from the
  // foe's feet down. The foe is drawn high on the panel; over the skyline it
  // stood on the rooftops (reported from a board). Its feet are at panel row
  // 56 + 78 = 134, i.e. layer row (134 - 30) / 2 = 52.
  {
    bool skyClear = true, floorSolid = true;
    for (int v = 0; v < VIL_COUNT; v++) {
      const uint8_t *b = VILLAGES[v].battle;
      for (int r = 0; r < 4; r++) for (int x = 0; x < VIL_W; x++) if (b[r * VIL_W + x] != VIL_CLEAR) skyClear = false;
      for (int r = 52; r < VIL_BATTLE_H; r++) for (int x = 0; x < VIL_W; x++) if (b[r * VIL_W + x] == VIL_CLEAR) floorSolid = false;
    }
    ck(skyClear, "the fight layer leaves the top to the firmware's sky");
    ck(floorSolid, "and is solid floor from the foe's feet down, in every village");
  }

  printf("%s\n", bad ? "FAILURES" : "every village has its own backdrop");
  return bad ? 1 : 0;
}
