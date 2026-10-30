// RANKS: in this game a ninja keeps the rank it has in the series.
//
// The engine underneath still has the digivolution machinery (EVO_TBL,
// digiTarget, the stage clock), and that is fine as long as it is provably
// idle. These tests pin what replaced it: every ninja carries its canonical
// rank, nothing is ever offered a change into somebody else at any age or
// record, a Genin still reaches its farewell, and missions are ranked by level.
#include "Arduino.h"
#include "Preferences.h"
#include "pet.h"
#include "dex.h"
#include "noart.h"
#include "moves.h"
#include "wild.h"
#include <cstdio>
#include <cstring>
#ifndef TAMA_NATIVE_TEST
uint32_t g_seed = 99;
FakeSerial Serial; FakeESP ESP; FakeWire Wire;
volatile int g_touchX=0, g_touchY=0; volatile bool g_touchDown=false;
bool wasPressed=false;
uint32_t millis(){ return 0; }
void FakeESP::restart(){ exit(0); }
int FakeSerial::available(){ return 0; }
String FakeSerial::readStringUntil(char){ return String(""); }
void sfxPlay(uint8_t){}
#endif

static int bad=0;
static void ck(bool ok,const char*w){ printf("%s  %s\n",ok?"PASS":"FAIL",w); if(!ok)bad++; }

static int16_t byName(const char *n) {
  for (int16_t d = 1; d <= DEX_COUNT; d++) if (!strcmp(DEX_TBL[d].name, n)) return d;
  return 0;
}

int main() {
  // --- canonical ranks, by name rather than by dex number
  struct { const char *who; uint8_t rank; } canon[] = {
    { "KONOHAMARU", ST_BABY2 }, { "NARUTO", ST_ROOKIE }, { "GAARA", ST_ROOKIE },
    { "SHIKAMARU", ST_CHAMPION }, { "KAKASHI", ST_ULTIMATE }, { "ZABUZA", ST_ULTIMATE },
    { "HIRUZEN", ST_MEGA }, { "OROCHIMARU", ST_MEGA },
  };
  int wrong = 0;
  for (auto &c : canon) {
    int16_t d = byName(c.who);
    if (!d || DEX_TBL[d].stage != c.rank) { printf("      %s: rank %d\n", c.who, d ? DEX_TBL[d].stage : -1); wrong++; }
  }
  ck(wrong == 0, "every ninja carries its rank from the series");

  // --- nobody turns into anybody: not at any age, not with any record
  ck(EVO_COUNT == 0, "the branch table is empty");
  int offered = 0, pointing = 0;
  for (int16_t d = 1; d <= DEX_COUNT; d++) {
    if (DEX_TBL[d].evolvesTo || DEX_TBL[d].evolveLevel) pointing++;
    Pet p; p.begin(); p.dbgHatchAs(d, false);
    for (uint8_t lvl : { 2, 7, 25, 49, 61, 100 }) {
      p.ageMinutes = (uint32_t)(lvl - 1) * MINUTES_PER_LEVEL;
      p.careMistakes = 0; p.trAtk = p.trDef = p.trSpe = 80; p.wins = 60;
      if (p.digiTarget() || p.canEvolveNow()) offered++;
    }
  }
  ck(pointing == 0, "and no dex entry points at a next form");
  ck(offered == 0, "so no ninja is ever offered a rank change, whatever its age or wins");

  // --- a Genin still reaches the end of its run (the old rule wanted Champion+)
  {
    Pet p; p.begin(); p.dbgHatchAs(byName("NARUTO"), false);
    p.fullness = p.joy = p.energy = p.hygiene = 100;
    p.ageMinutes = FAREWELL_AGE_MIN - 1;
    ck(!p.canFarewellNow(), "a young Genin is not ready to say goodbye");
    p.ageMinutes = FAREWELL_AGE_MIN;
    ck(p.canFarewellNow(), "and after its three days it is -- a Genin is not stuck forever");
  }

  // --- wins still count (they feed the training reward and the record)
  {
    Pet p; p.begin(); p.dbgHatchAs(byName("SASUKE"), false);
    uint8_t w = p.wins;
    p.addWin();
    ck(p.wins == w + 1, "a won battle is still counted");
  }

  // --- missions are ranked by level, and every village always has someone
  ck(wildStageForLevel(10) == ST_ROOKIE && wildStageForLevel(30) == ST_CHAMPION &&
     wildStageForLevel(55) == ST_ULTIMATE && wildStageForLevel(70) == ST_MEGA,
     "a mission's rank follows the level: Genin, Chunin, Jonin, Kage");
  {
    int empty = 0;
    for (uint8_t r = 0; r < REGION_COUNT - 1; r++) {
      bool any = false;
      for (int16_t d = REGIONS[r].lo; d <= REGIONS[r].hi; d++) if (speciesHasArt(d)) any = true;
      if (!any) empty++;
    }
    ck(empty == 0, "every village has somebody to meet on a mission");
  }

  // --- jutsu are reachable from level 1 (a Jonin out of a scroll is not empty-handed)
  {
    Pet p; p.begin(); p.dbgHatchAs(byName("KAKASHI"), false);
    p.ageMinutes = 0;
    p.relearnFromLevel();
    int attacks = 0;
    for (int i = 0; i < MOVE_SLOTS; i++)
      if (p.moves[i] && MOVE_TBL[p.moves[i]].power) attacks++;
    ck(attacks >= 1, "a level 1 KAKASHI has an attack");
    ck(p.moveCount() >= 2, "and more than one move to choose from");
  }

  printf("%s\n", bad ? "FAILURES" : "all good");
  return bad ? 1 : 0;
}
