

 
  #include "CAoJia.h"

  fnSetDllPathW CARegJ::pfnSetDllPathW = NULL;
  
  LONG CARegJ::SetDllPathW(LPCWSTR ARegJPath, LPCWSTR AoJiaPath) {
    LONG lr = 0;
    if (pfnSetDllPathW == NULL) {
      HMODULE hDll = LoadLibraryW(ARegJPath);
      if (hDll != NULL) {
        pfnSetDllPathW = (fnSetDllPathW)GetProcAddress(hDll, "SetDllPathW");
      }
    }
    if (pfnSetDllPathW != NULL) {
      lr = pfnSetDllPathW(AoJiaPath, 0);
    }
    return lr;
  }
  
  CAoJia::CAoJia() {
    //函数CoCreateInstance会去注册表查询插件的信息,如果查询不到就不能创建对象
    //如果不想使用免注册调用插件,可以先向系统注册表注册插件,然后调用这个无参构造函数创建对象
    pIDispatch = NULL; hr = CoCreateInstance(clsid, NULL, CLSCTX_INPROC_SERVER, IID_IDispatch, (LPVOID*)&pIDispatch);
  }
  
  CAoJia::CAoJia(LPCWSTR ARegJPath, LPCWSTR AoJiaPath) {
    CARegJ::SetDllPathW(ARegJPath, AoJiaPath);//有了这句代码就是免注册调用插件,即使注册表没有插件的信息也能创建对象
    pIDispatch = NULL; hr = CoCreateInstance(clsid, NULL, CLSCTX_INPROC_SERVER, IID_IDispatch, (LPVOID*)&pIDispatch);
  }
  
  CAoJia::~CAoJia() {
    if (pIDispatch != NULL) {
      pIDispatch->Release();
    }
  }
  
  HRESULT CAoJia::Call(LPCWSTR FunName, DISPID* rgdispid, DISPPARAMS* pDispParams, VARIANT* pvarResult) {
    if (*rgdispid == -1) {
      pIDispatch->GetIDsOfNames(IID_NULL, (LPOLESTR*)&FunName, 1, LOCALE_SYSTEM_DEFAULT, rgdispid);
    }
    return pIDispatch->Invoke(*rgdispid, IID_NULL, LOCALE_SYSTEM_DEFAULT, DISPATCH_METHOD, pDispParams, pvarResult, NULL, NULL);
  }
  
  CString CAoJia::VerS() {
    LPCWSTR FunName = L"VerS"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SetPath(LPCWSTR Path) {
    COleVariant v[1]; v[0] = COleVariant(Path);
    LPCWSTR FunName = L"SetPath"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetErrorMsg(LONG Msg) {
    COleVariant v[1]; v[0] = COleVariant(Msg);
    LPCWSTR FunName = L"SetErrorMsg"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetThread(LONG TN) {
    COleVariant v[1]; v[0] = COleVariant(TN);
    LPCWSTR FunName = L"SetThread"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetModulePath(LONG PID, LONG Hwnd, LPCWSTR MN, LONG Type) {
    COleVariant v[4]; v[0] = COleVariant(Type); v[1] = COleVariant(MN); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"GetModulePath"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::GetMachineCode() {
    LPCWSTR FunName = L"GetMachineCode"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::GetOs(CString& SV, CString& SVN, LONG& LVBN, CString& SDir, LONG Type) {
    CComVariant V, VN, VBN, Dir;
    COleVariant v[5]; v[0] = COleVariant(Type); v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &Dir; v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &VBN;
    v[3].vt = VT_BYREF | VT_VARIANT; v[3].pvarVal = &VN; v[4].vt = VT_BYREF | VT_VARIANT; v[4].pvarVal = &V;
    LPCWSTR FunName = L"GetOs"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      SV = V.bstrVal; SVN = VN.bstrVal; LVBN = VBN.lVal; SDir = Dir.bstrVal; return rt.lVal;
    }
    SV = L""; SVN = L""; LVBN = -1; SDir = L""; return 0;
  }
  
  LONG CAoJia::FindWindow(LONG Parent, LPCWSTR ProName, LONG ProID, LPCWSTR Class, LPCWSTR Title, LONG Type, LONG T) {
    COleVariant v[7]; v[0] = COleVariant(T); v[1] = COleVariant(Type); v[2] = COleVariant(Title); v[3] = COleVariant(Class); v[4] = COleVariant(ProID);
    v[5] = COleVariant(ProName); v[6] = COleVariant(Parent);
    LPCWSTR FunName = L"FindWindow"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CreateWindows(LONG x, LONG y, LONG Width, LONG Height, LONG EWidth, LONG EHeight, LONG Type) {
    COleVariant v[7]; v[0] = COleVariant(Type); v[1] = COleVariant(EHeight); v[2] = COleVariant(EWidth); v[3] = COleVariant(Height); v[4] = COleVariant(Width);
    v[5] = COleVariant(y); v[6] = COleVariant(x);
    LPCWSTR FunName = L"CreateWindows"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONGLONG CAoJia::GetRemoteProcAddress(LONG PID, LONG Hwnd, LPCWSTR MN, LPCWSTR Func) {
    COleVariant v[4]; v[0] = COleVariant(Func); v[1] = COleVariant(MN); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"GetRemoteProcAddress"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.llVal;
    }
    return 0;
  }
  
  LONG CAoJia::ClientToScreen(LONG Hwnd, LONG& x, LONG& y) {
    CComVariant xv, yv; xv.vt = VT_I4; xv.lVal = x; yv.vt = VT_I4; yv.lVal = y;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &yv; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &xv; v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"ClientToScreen"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = xv.lVal; y = yv.lVal; return rt.lVal;
    }
    return 0;
  }

  LONG CAoJia::ClientOrScreen(LONG Hwnd, LONG xz, LONG yz, LONG& x, LONG& y, LONG Type) {
    CComVariant xv, yv;
    COleVariant v[6]; v[0] = COleVariant(Type); v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &yv; v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &xv;
    v[3] = COleVariant(yz); v[4] = COleVariant(xz); v[5] = COleVariant(Hwnd);
    LPCWSTR FunName = L"ClientOrScreen"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = xv.lVal; y = yv.lVal; return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CompressFile(LPCWSTR SF, LPCWSTR DF, LONG Type, LONG Level) {
    COleVariant v[4]; v[0] = COleVariant(Level); v[1] = COleVariant(Type); v[2] = COleVariant(DF); v[3] = COleVariant(SF);
    LPCWSTR FunName = L"CompressFile"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::UnCompressFile(LPCWSTR SF, LPCWSTR DF, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(DF); v[2] = COleVariant(SF);
    LPCWSTR FunName = L"UnCompressFile"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetFont(LONG Hwnd, LPCWSTR Name, LONG Size, LONG Weight, LONG Italic, LONG Underline, LONG StrikeOut) {
    COleVariant v[7]; v[0] = COleVariant(StrikeOut); v[1] = COleVariant(Underline); v[2] = COleVariant(Italic); v[3] = COleVariant(Weight);
    v[4] = COleVariant(Size); v[5] = COleVariant(Name); v[6] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetFont"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetTextD(LONG Hwnd, LONG x1, LONG y1, LONG x2, LONG y2, LONG Row, LONG Dir) {
    COleVariant v[7]; v[0] = COleVariant(Dir); v[1] = COleVariant(Row); v[2] = COleVariant(y2); v[3] = COleVariant(x2);
    v[4] = COleVariant(y1); v[5] = COleVariant(x1); v[6] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetTextD"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DrawTextD(LONG Hwnd, LPCWSTR Text, LPCWSTR Color, LPCWSTR BkColor) {
    COleVariant v[4]; v[0] = COleVariant(BkColor); v[1] = COleVariant(Color); v[2] = COleVariant(Text); v[3] = COleVariant(Hwnd);
    LPCWSTR FunName = L"DrawTextD"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CreateFolder(LPCWSTR FN) {
    COleVariant v[1]; v[0] = COleVariant(FN);
    LPCWSTR FunName = L"CreateFolder"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::FindFile(LPCWSTR FN) {
    COleVariant v[1]; v[0] = COleVariant(FN);
    LPCWSTR FunName = L"FindFile"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::IsFileOrFolder(LPCWSTR FN) {
    COleVariant v[1]; v[0] = COleVariant(FN);
    LPCWSTR FunName = L"IsFileOrFolder"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::IsFileOrFolderE(LPCWSTR FN) {
    COleVariant v[1]; v[0] = COleVariant(FN);
    LPCWSTR FunName = L"IsFileOrFolderE"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CopyFile(LPCWSTR SF, LPCWSTR DF, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(DF); v[2] = COleVariant(SF);
    LPCWSTR FunName = L"CopyFile"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CopyFolder(LPCWSTR SF, LPCWSTR DF, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(DF); v[2] = COleVariant(SF);
    LPCWSTR FunName = L"CopyFolder"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DeleteFile(LPCWSTR FN) {
    COleVariant v[1]; v[0] = COleVariant(FN);
    LPCWSTR FunName = L"DeleteFile"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DeleteFolder(LPCWSTR FN) {
    COleVariant v[1]; v[0] = COleVariant(FN);
    LPCWSTR FunName = L"DeleteFolder"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetPCData(LONG Type, LPCWSTR PicName) {
    COleVariant v[2]; v[0] = COleVariant(PicName); v[1] = COleVariant(Type);
    LPCWSTR FunName = L"SetPCData"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetGlobalDict(LONG GD) {
    COleVariant v[1]; v[0] = COleVariant(GD);
    LPCWSTR FunName = L"SetGlobalDict"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetLastError() {
    LPCWSTR FunName = L"GetLastError"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetPicCache(LONG PicD) {
    COleVariant v[1]; v[0] = COleVariant(PicD);
    LPCWSTR FunName = L"SetPicCache"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetPath() {
    LPCWSTR FunName = L"GetPath"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::GetAoJiaID() {
    LPCWSTR FunName = L"GetAoJiaID"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetAoJiaNum() {
    LPCWSTR FunName = L"GetAoJiaNum"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetExcludeArea(LONG Type, LPCWSTR AreaD) {
    COleVariant v[2]; v[0] = COleVariant(AreaD); v[1] = COleVariant(Type);
    LPCWSTR FunName = L"SetExcludeArea"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetPicPw(LPCWSTR Pw) {
    COleVariant v[1]; v[0] = COleVariant(Pw);
    LPCWSTR FunName = L"SetPicPw"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetDictPw(LPCWSTR Pw) {
    COleVariant v[1]; v[0] = COleVariant(Pw);
    LPCWSTR FunName = L"SetDictPw"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetDesktopArea(LONG Hwnd, LONG Dx1, LONG Dy1, LONG Dx2, LONG Dy2, LONG Flag, LONG Type) {
    COleVariant v[7]; v[0] = COleVariant(Type); v[1] = COleVariant(Flag); v[2] = COleVariant(Dy2); v[3] = COleVariant(Dx2); v[4] = COleVariant(Dy1); v[5] = COleVariant(Dx1);
    v[6] = COleVariant(Hwnd); LPCWSTR FunName = L"SetDesktopArea"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::EnumProcess(LPCWSTR ProName) {
    COleVariant v[1]; v[0] = COleVariant(ProName);
    LPCWSTR FunName = L"EnumProcess"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::TerminateProcess(LONG PID, LONG Hwnd, LPCWSTR ProName, LONG Type) {
    COleVariant v[4]; v[0] = COleVariant(Type); v[1] = COleVariant(ProName); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"TerminateProcess"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  CString CAoJia::GetProcessInfo(LONG PID, LONG Hwnd) {
    COleVariant v[2]; v[0] = COleVariant(Hwnd); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"GetProcessInfo"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::DisableIME(LONG TID, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(TID);
    LPCWSTR FunName = L"DisableIME"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::EnumThread(LONG PID, LONG Hwnd) {
    COleVariant v[2]; v[0] = COleVariant(Hwnd); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"EnumThread"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::GetCurrentThreadId() {
    LPCWSTR FunName = L"GetCurrentThreadId"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::TerminateThread(LONG TID) {
    COleVariant v[1]; v[0] = COleVariant(TID);
    LPCWSTR FunName = L"TerminateThread"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetCurrentProcessId() {
    LPCWSTR FunName = L"GetCurrentProcessId"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetProcessPath(LONG PID, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"GetProcessPath"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::GetPTNum(LONG& PS, LONG& HC, LONG& TC) {
    CComVariant vPS, vHC, vTC;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vTC; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vHC;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vPS;
    LPCWSTR FunName = L"GetPTNum"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      PS = vPS.lVal; HC = vHC.lVal; TC = vTC.lVal; return rt.lVal;
    }
    PS = -1; HC = -1; TC = -1; return -1;
  }
  
  CString CAoJia::GetCommandLine(LONG PID, LONG Hwnd) {
    COleVariant v[2]; v[0] = COleVariant(Hwnd); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"GetCommandLine"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::EnumModule(LONG PID, LONG Hwnd) {
    COleVariant v[2]; v[0] = COleVariant(Hwnd); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"EnumModule"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONGLONG CAoJia::GetModuleBaseAddr(LONG PID, LONG Hwnd, LPCWSTR MN) {
    COleVariant v[3]; v[0] = COleVariant(MN); v[1] = COleVariant(Hwnd); v[2] = COleVariant(PID);
    LPCWSTR FunName = L"GetModuleBaseAddr"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.llVal;
    }
    return 0;
  }
  
  ULONG CAoJia::GetModuleSize(LONG PID, LONG Hwnd, LPCWSTR MN) {
    COleVariant v[3]; v[0] = COleVariant(MN); v[1] = COleVariant(Hwnd); v[2] = COleVariant(PID);
    LPCWSTR FunName = L"GetModuleSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.ulVal;
    }
    return 0;
  }
  
  LONG CAoJia::Is64Process(LONG PID, LONG Hwnd) {
    COleVariant v[2]; v[0] = COleVariant(Hwnd); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"Is64Process"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::FindWindowEx(LPCWSTR Scdt1, LONG Flag1, LONG Type1, LPCWSTR Scdt2, LONG Flag2, LONG Type2, LPCWSTR Scdt3, LONG Flag3, LONG Type3, LONG Visible, LONG T) {
    COleVariant v[11]; v[0] = COleVariant(T); v[1] = COleVariant(Visible); v[2] = COleVariant(Type3); v[3] = COleVariant(Flag3); v[4] = COleVariant(Scdt3);
    v[5] = COleVariant(Type2); v[6] = COleVariant(Flag2); v[7] = COleVariant(Scdt2); v[8] = COleVariant(Type1); v[9] = COleVariant(Flag1); v[10] = COleVariant(Scdt1);
    LPCWSTR FunName = L"FindWindowEx"; DISPPARAMS dp = { v,NULL,11,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::EnumWindow(LONG Parent, LPCWSTR ProName, LONG ProID, LPCWSTR Class, LPCWSTR Title, LONG Type, LONG Flag, LONG T) {
    COleVariant v[8]; v[0] = COleVariant(T); v[1] = COleVariant(Flag); v[2] = COleVariant(Type); v[3] = COleVariant(Title); v[4] = COleVariant(Class);
    v[5] = COleVariant(ProID); v[6] = COleVariant(ProName); v[7] = COleVariant(Parent);
    LPCWSTR FunName = L"EnumWindow"; DISPPARAMS dp = { v,NULL,8,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::EnumWindowEx(LPCWSTR Scdt1, LONG Flag1, LONG Type1, LPCWSTR Scdt2, LONG Flag2, LONG Type2, LPCWSTR Scdt3, LONG Flag3, LONG Type3, LONG Visible, LONG Sort, LONG T) {
    COleVariant v[12]; v[0] = COleVariant(T); v[1] = COleVariant(Sort); v[2] = COleVariant(Visible); v[3] = COleVariant(Type3); v[4] = COleVariant(Flag3);
    v[5] = COleVariant(Scdt3); v[6] = COleVariant(Type2); v[7] = COleVariant(Flag2); v[8] = COleVariant(Scdt2); v[9] = COleVariant(Type1); v[10] = COleVariant(Flag1);
    v[11] = COleVariant(Scdt1);
    LPCWSTR FunName = L"EnumWindowEx"; DISPPARAMS dp = { v,NULL,12,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::GetWindowClass(LONG Hwnd) {
    COleVariant v[1]; v[0] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowClass"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::GetWindowTitle(LONG Hwnd) {
    COleVariant v[1]; v[0] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowTitle"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SetWindowTitle(LONG Hwnd, LPCWSTR Title) {
    COleVariant v[2]; v[0] = COleVariant(Title); v[1] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetWindowTitle"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetClientRect(LONG Hwnd, LONG& x1, LONG& y1, LONG& x2, LONG& y2) {
    CComVariant vx1, vy1, vx2, vy2;
    COleVariant v[5]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy2; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx2;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vy1; v[3].vt = VT_BYREF | VT_VARIANT; v[3].pvarVal = &vx1; v[4] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetClientRect"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x1 = vx1.lVal; y1 = vy1.lVal; x2 = vx2.lVal; y2 = vy2.lVal; return rt.lVal;
    }
    x1 = -1; y1 = -1; x2 = -1; y2 = -1; return 0;
  }
  
  LONG CAoJia::GetClientSize(LONG Hwnd, LONG& Width, LONG& Height) {
    CComVariant vWidth, vHeight;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vWidth; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vHeight; v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetClientSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Width = vWidth.lVal; Height = vHeight.lVal; return rt.lVal;
    }
    Width = -1; Height = -1; return 0;
  }
  
  LONG CAoJia::GetWindowRect(LONG Hwnd, LONG& x1, LONG& y1, LONG& x2, LONG& y2, LONG Type) {
    CComVariant vx1, vy1, vx2, vy2;
    COleVariant v[6]; v[0] = COleVariant(Type); v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vy2; v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vx2;
    v[3].vt = VT_BYREF | VT_VARIANT; v[3].pvarVal = &vy1; v[4].vt = VT_BYREF | VT_VARIANT; v[4].pvarVal = &vx1; v[5] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowRect"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x1 = vx1.lVal; y1 = vy1.lVal; x2 = vx2.lVal; y2 = vy2.lVal; return rt.lVal;
    }
    x1 = -1; y1 = -1; x2 = -1; y2 = -1; return 0;
  }
  
  LONG CAoJia::GetWindowSize(LONG Hwnd, LONG& Width, LONG& Height) {
    CComVariant vWidth, vHeight;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vWidth; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vHeight; v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Width = vWidth.lVal; Height = vHeight.lVal; return rt.lVal;
    }
    Width = -1; Height = -1; return 0;
  }
  
  LONG CAoJia::ScreenToClient(LONG Hwnd, LONG& x, LONG& y) {
    CComVariant xv, yv; xv.vt = VT_I4; xv.lVal = x; yv.vt = VT_I4; yv.lVal = y;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &yv; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &xv; v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"ScreenToClient"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = xv.lVal; y = yv.lVal; return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetClientSize(LONG Hwnd, LONG Width, LONG Height) {
    COleVariant v[3]; v[0] = COleVariant(Height); v[1] = COleVariant(Width); v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetClientSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetWindowSize(LONG Hwnd, LONG Width, LONG Height) {
    COleVariant v[3]; v[0] = COleVariant(Height); v[1] = COleVariant(Width); v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetWindowSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveWindow(LONG Hwnd, LONG x, LONG y) {
    COleVariant v[3]; v[0] = COleVariant(y); v[1] = COleVariant(x); v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"MoveWindow"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetWindowState(LONG Hwnd, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowState"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::SetWindowState(LONG Hwnd, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetWindowState"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::GetWindowThreadProcessId(LONG Hwnd, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowThreadProcessId"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetWindowProcessPath(LONG Hwnd, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindowProcessPath"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SetWindowTransparent(LONG Hwnd, LPCWSTR Color, LONG Tp, LONG Type) {
    COleVariant v[4]; v[0] = COleVariant(Type); v[1] = COleVariant(Tp); v[2] = COleVariant(Color); v[3] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetWindowTransparent"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetForegroundWindow() {
    LPCWSTR FunName = L"GetForegroundWindow"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetFocus() {
    LPCWSTR FunName = L"GetFocus"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetWindowFromPoint(LONG x, LONG y) {
    COleVariant v[2]; v[0] = COleVariant(y); v[1] = COleVariant(x);
    LPCWSTR FunName = L"GetWindowFromPoint"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetWindowFromMouse() {
    LPCWSTR FunName = L"GetWindowFromMouse"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetWindow(LONG Hwnd, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Hwnd);
    LPCWSTR FunName = L"GetWindow"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CloseWindow(LONG Hwnd) {
    COleVariant v[1]; v[0] = COleVariant(Hwnd);
    LPCWSTR FunName = L"CloseWindow"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::FillRect(LONG Hwnd, LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color) {
    COleVariant v[6]; v[0] = COleVariant(Color); v[1] = COleVariant(y2); v[2] = COleVariant(x2); v[3] = COleVariant(y1); v[4] = COleVariant(x1);
    v[5] = COleVariant(Hwnd);
    LPCWSTR FunName = L"FillRect"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DrawLine(LONG Hwnd, LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, LONG Width, LONG Style) {
    COleVariant v[8]; v[0] = COleVariant(Style); v[1] = COleVariant(Width); v[2] = COleVariant(Color); v[3] = COleVariant(y2); v[4] = COleVariant(x2);
    v[5] = COleVariant(y1); v[6] = COleVariant(x1); v[7] = COleVariant(Hwnd);
    LPCWSTR FunName = L"DrawLine"; DISPPARAMS dp = { v,NULL,8,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DrawPic(LONG Hwnd, LONG x, LONG y, LPCWSTR Color, LPCWSTR PicName) {
    COleVariant v[5]; v[0] = COleVariant(PicName); v[1] = COleVariant(Color); v[2] = COleVariant(y); v[3] = COleVariant(x); v[4] = COleVariant(Hwnd);
    LPCWSTR FunName = L"DrawPic"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetCHwndSize(LONG Hwnd, LONG Width, LONG Height) {
    COleVariant v[3]; v[0] = COleVariant(Height); v[1] = COleVariant(Width); v[2] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SetCHwndSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DrawGif(LONG Hwnd, LONG x, LONG y, LPCWSTR PicName, LONG TD, LONG Num) {
    COleVariant v[6]; v[0] = COleVariant(Num); v[1] = COleVariant(TD); v[2] = COleVariant(PicName); v[3] = COleVariant(y); v[4] = COleVariant(x);
    v[5] = COleVariant(Hwnd);
    LPCWSTR FunName = L"DrawGif"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::StopGif(LONG Hwnd, LONG x, LONG y, LPCWSTR PicName) {
    COleVariant v[4]; v[0] = COleVariant(PicName); v[1] = COleVariant(y); v[2] = COleVariant(x); v[3] = COleVariant(Hwnd);
    LPCWSTR FunName = L"StopGif"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DrawText(LONG Hwnd, LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Text, LPCWSTR Color, LPCWSTR BkColor, LONG Type) {
    COleVariant v[9]; v[0] = COleVariant(Type); v[1] = COleVariant(BkColor); v[2] = COleVariant(Color); v[3] = COleVariant(Text);
    v[4] = COleVariant(y2); v[5] = COleVariant(x2); v[6] = COleVariant(y1); v[7] = COleVariant(x1); v[8] = COleVariant(Hwnd);
    LPCWSTR FunName = L"DrawText"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::ClearTextD(LONG Hwnd) {
    COleVariant v[1]; v[0] = COleVariant(Hwnd);
    LPCWSTR FunName = L"ClearTextD"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetCreateWindows(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetCreateWindows"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::OpenFolder(LPCWSTR Fd) {
    COleVariant v[1]; v[0] = COleVariant(Fd);
    LPCWSTR FunName = L"OpenFolder"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveFile(LPCWSTR SF, LPCWSTR DF, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(DF); v[2] = COleVariant(SF);
    LPCWSTR FunName = L"MoveFile"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetFileAttribute(LPCWSTR FN, LONG& RD, LONG& HD) {
    CComVariant vRD, vHD;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vHD; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vRD; v[2] = COleVariant(FN);
    LPCWSTR FunName = L"GetFileAttribute"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      RD = vRD.lVal; HD = vHD.lVal; return rt.lVal;
    }
    RD = -1; HD = -1; return 0;
  }
  
  LONG CAoJia::SetFileAttribute(LPCWSTR FN, LONG RD, LONG HD) {
    COleVariant v[3]; v[0] = COleVariant(HD); v[1] = COleVariant(RD); v[2] = COleVariant(FN);
    LPCWSTR FunName = L"SetFileAttribute"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetFileTime(LPCWSTR FN, CString& CT, CString& WT, CString& AT) {
    CComVariant vCT, vWT, vAT;
    COleVariant v[4]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vAT; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vWT;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vCT; v[3] = COleVariant(FN);
    LPCWSTR FunName = L"GetFileTime"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      CT = vCT.bstrVal; WT = vWT.bstrVal; AT = vAT.bstrVal; return rt.lVal;
    }
    CT = L""; WT = L""; AT = L""; return 0;
  }
  
  LONG CAoJia::SetFileTime(LPCWSTR FN, LPCWSTR CT, LPCWSTR WT, LPCWSTR AT) {
    COleVariant v[4]; v[0] = COleVariant(AT); v[1] = COleVariant(WT); v[2] = COleVariant(CT); v[3] = COleVariant(FN);
    LPCWSTR FunName = L"SetFileTime"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  DOUBLE CAoJia::GetFileSize(LPCWSTR FN, LONG& FSH, LONG& FSL) {
    CComVariant vFSH, vFSL;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vFSL; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vFSH; v[2] = COleVariant(FN);
    LPCWSTR FunName = L"GetFileSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      FSH = vFSH.lVal; FSL = vFSL.lVal; return rt.dblVal;
    }
    FSH = -1; FSL = -1; return -1.0;
  }
  
  LONG CAoJia::CompareFileTime(LPCWSTR FN, LPCWSTR FND, LONG& CT, LONG& WT, LONG& AT) {
    CComVariant vCT, vWT, vAT;
    COleVariant v[5]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vAT; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vWT;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vCT; v[3] = COleVariant(FND); v[4] = COleVariant(FN);
    LPCWSTR FunName = L"CompareFileTime"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      CT = vCT.lVal; WT = vWT.lVal; AT = vAT.lVal; return rt.lVal;
    }
    CT = -2; WT = -2; AT = -2; return 0;
  }
  
  LONG CAoJia::MoveFolder(LPCWSTR SF, LPCWSTR DF, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(DF); v[2] = COleVariant(SF);
    LPCWSTR FunName = L"MoveFolder"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::ReNameFile(LPCWSTR SF, LPCWSTR DF) {
    COleVariant v[2]; v[0] = COleVariant(DF); v[1] = COleVariant(SF);
    LPCWSTR FunName = L"ReNameFile"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::SelectFileOrFolder() {
    LPCWSTR FunName = L"SelectFileOrFolder"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::WriteIni(LPCWSTR FN, LPCWSTR Section, LPCWSTR Key, LPCWSTR Value, LPCWSTR Pw) {
    COleVariant v[5]; v[0] = COleVariant(Pw); v[1] = COleVariant(Value); v[2] = COleVariant(Key); v[3] = COleVariant(Section); v[4] = COleVariant(FN);
    LPCWSTR FunName = L"WriteIni"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::ReadIni(LPCWSTR FN, LPCWSTR Section, LPCWSTR Key, LPCWSTR Pw) {
    COleVariant v[4]; v[0] = COleVariant(Pw); v[1] = COleVariant(Key); v[2] = COleVariant(Section); v[3] = COleVariant(FN);
    LPCWSTR FunName = L"ReadIni"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::DeleteIni(LPCWSTR FN, LPCWSTR Section, LPCWSTR Key, LPCWSTR Pw) {
    COleVariant v[4]; v[0] = COleVariant(Pw); v[1] = COleVariant(Key); v[2] = COleVariant(Section); v[3] = COleVariant(FN);
    LPCWSTR FunName = L"DeleteIni"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::EnumIni(LPCWSTR FN, LPCWSTR Section, LPCWSTR Pw) {
    COleVariant v[3]; v[0] = COleVariant(Pw); v[1] = COleVariant(Section); v[2] = COleVariant(FN);
    LPCWSTR FunName = L"EnumIni"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::EncryptFile(LPCWSTR FN, LPCWSTR Pw) {
    COleVariant v[2]; v[0] = COleVariant(Pw); v[1] = COleVariant(FN);
    LPCWSTR FunName = L"EncryptFile"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DecryptFile(LPCWSTR FN, LPCWSTR Pw) {
    COleVariant v[2]; v[0] = COleVariant(Pw); v[1] = COleVariant(FN);
    LPCWSTR FunName = L"DecryptFile"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::ReadFile(LPCWSTR FN, LONG Pos, LONG Flag, LONG Size, LONG Type, LONG TypeD) {
    COleVariant v[6]; v[0] = COleVariant(TypeD); v[1] = COleVariant(Type); v[2] = COleVariant(Size); v[3] = COleVariant(Flag); v[4] = COleVariant(Pos);
    v[5] = COleVariant(FN);
    LPCWSTR FunName = L"ReadFile"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::WriteFile(LPCWSTR FN, LPCWSTR Str, LONG Pos, LONG Flag, LONG Size, LONG Type, LONG TypeD) {
    COleVariant v[7]; v[0] = COleVariant(TypeD); v[1] = COleVariant(Type); v[2] = COleVariant(Size); v[3] = COleVariant(Flag); v[4] = COleVariant(Pos);
    v[5] = COleVariant(Str); v[6] = COleVariant(FN);
    LPCWSTR FunName = L"WriteFile"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::CompareFileData(LPCWSTR SN1, LPCWSTR SN2) {
    COleVariant v[2]; v[0] = COleVariant(SN2); v[1] = COleVariant(SN1);
    LPCWSTR FunName = L"CompareFileData"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  CString CAoJia::DoubleToData(DOUBLE db) {
    COleVariant v[1]; v[0] = COleVariant(db);
    LPCWSTR FunName = L"DoubleToData"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::FloatToData(FLOAT fl) {
    COleVariant v[1]; v[0] = COleVariant(fl);
    LPCWSTR FunName = L"FloatToData"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::IntToData(LONG i, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(i);
    LPCWSTR FunName = L"IntToData"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::Int64ToData(LONGLONG i64, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(i64);
    LPCWSTR FunName = L"Int64ToData"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::StringToData(LPCWSTR Str, LONG Type, LONG Flag) {
    COleVariant v[3]; v[0] = COleVariant(Flag); v[1] = COleVariant(Type); v[2] = COleVariant(Str);
    LPCWSTR FunName = L"StringToData"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FreeProcessMemory(LONG PID, LONG Hwnd) {
    COleVariant v[2]; v[0] = COleVariant(Hwnd); v[1] = COleVariant(PID);
    LPCWSTR FunName = L"FreeProcessMemory"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONGLONG CAoJia::VirtualAllocEx(LONG PID, LONG Hwnd, LONGLONG Addr, ULONG Size, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant((ULONGLONG)Size); v[2] = COleVariant(Addr); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"VirtualAllocEx"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.llVal;
    }
    return 0;
  }
  
  LONG CAoJia::VirtualFreeEx(LONG PID, LONG Hwnd, LONGLONG Addr) {
    COleVariant v[3]; v[0] = COleVariant(Addr); v[1] = COleVariant(Hwnd); v[2] = COleVariant(PID);
    LPCWSTR FunName = L"VirtualFreeEx"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::VirtualQueryEx(LONG PID, LONG Hwnd, LONGLONG Addr, LONG& AProtect, LONG& Protect, LONG& State, LONG& Type) {
    CComVariant vAProtect, vProtect, vState, vType;
    COleVariant v[7]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vState;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vProtect; v[3].vt = VT_BYREF | VT_VARIANT; v[3].pvarVal = &vAProtect;
    v[4] = COleVariant(Addr); v[5] = COleVariant(Hwnd); v[6] = COleVariant(PID);
    LPCWSTR FunName = L"VirtualQueryEx"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      AProtect = vAProtect.lVal; Protect = vProtect.lVal; State = vState.lVal; Type = vType.lVal; return CString(rt.bstrVal);
    }
    AProtect = -1; Protect = -1; State = -1; Type = -1; return L"";
  }
  
  ULONG CAoJia::VirtualProtectEx(LONG PID, LONG Hwnd, LONGLONG Addr, ULONG Size, LONG Flag, ULONG Protect, LONG& Type) {
    CComVariant vType;
    COleVariant v[7]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant((ULONGLONG)Protect); v[2] = COleVariant(Flag);
    v[3] = COleVariant((ULONGLONG)Size); v[4] = COleVariant(Addr); v[5] = COleVariant(Hwnd); v[6] = COleVariant(PID);
    LPCWSTR FunName = L"VirtualProtectEx"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.ulVal;
    }
    Type = 0; return 0;
  }
  
  CString CAoJia::ReadDataS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONG Len) {
    COleVariant v[4]; v[0] = COleVariant(Len); v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadDataS"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::ReadDataL(LONG PID, LONG Hwnd, LONGLONG AddrL, LONG Len) {
    COleVariant v[4]; v[0] = COleVariant(Len); v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadDataL"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::WriteDataS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LPCWSTR Data) {
    COleVariant v[4]; v[0] = COleVariant(Data); v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"WriteDataS"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteDataL(LONG PID, LONG Hwnd, LONGLONG AddrL, LPCWSTR Data) {
    COleVariant v[4]; v[0] = COleVariant(Data); v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"WriteDataL"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONGLONG CAoJia::ReadDataSA(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONG Len) {
    COleVariant v[4]; v[0] = COleVariant(Len); v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadDataSA"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.llVal;
    }
    return 0;
  }
  
  LONGLONG CAoJia::ReadDataLA(LONG PID, LONG Hwnd, LONGLONG AddrL, LONG Len) {
    COleVariant v[4]; v[0] = COleVariant(Len); v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadDataLA"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.llVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteDataSA(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONGLONG Data, LONG Len) {
    COleVariant v[5]; v[0] = COleVariant(Len); v[1] = COleVariant(Data); v[2] = COleVariant(AddrS); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"WriteDataSA"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteDataLA(LONG PID, LONG Hwnd, LONGLONG AddrL, LONGLONG Data, LONG Len) {
    COleVariant v[5]; v[0] = COleVariant(Len); v[1] = COleVariant(Data); v[2] = COleVariant(AddrL); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"WriteDataLA"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  DOUBLE CAoJia::ReadDoubleS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONG& Type) {
    CComVariant vType;
    COleVariant v[4]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadDoubleS"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.dblVal;
    }
    Type = 0; return 0;
  }
  
  DOUBLE CAoJia::ReadDoubleL(LONG PID, LONG Hwnd, LONGLONG AddrL, LONG& Type) {
    CComVariant vType;
    COleVariant v[4]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadDoubleL"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.dblVal;
    }
    Type = 0; return 0;
  }
  
  LONG CAoJia::WriteDoubleS(LONG PID, LONG Hwnd, LPCWSTR AddrS, DOUBLE Db) {
    COleVariant v[4]; v[0] = COleVariant(Db); v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"WriteDoubleS"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteDoubleL(LONG PID, LONG Hwnd, LONGLONG AddrL, DOUBLE Db) {
    COleVariant v[4]; v[0] = COleVariant(Db); v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"WriteDoubleL"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  FLOAT CAoJia::ReadFloatS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONG& Type) {
    CComVariant vType;
    COleVariant v[4]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadFloatS"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.fltVal;
    }
    Type = 0; return 0;
  }
  
  FLOAT CAoJia::ReadFloatL(LONG PID, LONG Hwnd, LONGLONG AddrL, LONG& Type) {
    CComVariant vType;
    COleVariant v[4]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"ReadFloatL"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.fltVal;
    }
    Type = 0; return 0;
  }
  
  LONG CAoJia::WriteFloatS(LONG PID, LONG Hwnd, LPCWSTR AddrS, FLOAT Fl) {
    COleVariant v[4]; v[0] = COleVariant(Fl); v[1] = COleVariant(AddrS); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"WriteFloatS"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteFloatL(LONG PID, LONG Hwnd, LONGLONG AddrL, FLOAT Fl) {
    COleVariant v[4]; v[0] = COleVariant(Fl); v[1] = COleVariant(AddrL); v[2] = COleVariant(Hwnd); v[3] = COleVariant(PID);
    LPCWSTR FunName = L"WriteFloatL"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONGLONG CAoJia::ReadIntS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONG Flag, LONG& Type) {
    CComVariant vType;
    COleVariant v[5]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(Flag); v[2] = COleVariant(AddrS); v[3] = COleVariant(Hwnd);
    v[4] = COleVariant(PID);
    LPCWSTR FunName = L"ReadIntS"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.llVal;
    }
    Type = 0; return 0;
  }
  
  LONGLONG CAoJia::ReadIntL(LONG PID, LONG Hwnd, LONGLONG AddrL, LONG Flag, LONG& Type) {
    CComVariant vType;
    COleVariant v[5]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(Flag); v[2] = COleVariant(AddrL); v[3] = COleVariant(Hwnd);
    v[4] = COleVariant(PID);
    LPCWSTR FunName = L"ReadIntL"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return rt.llVal;
    }
    Type = 0; return 0;
  }
  
  LONG CAoJia::WriteIntS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONGLONG Ll, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant(Ll); v[2] = COleVariant(AddrS); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"WriteIntS"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteIntL(LONG PID, LONG Hwnd, LONGLONG AddrL, LONGLONG Ll, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant(Ll); v[2] = COleVariant(AddrL); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"WriteIntL"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::ReadStringS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONG Len, LONG Flag, LONG& Type) {
    CComVariant vType;
    COleVariant v[6]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(Flag); v[2] = COleVariant(Len); v[3] = COleVariant(AddrS);
    v[4] = COleVariant(Hwnd); v[5] = COleVariant(PID);
    LPCWSTR FunName = L"ReadStringS"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return CString(rt.bstrVal);
    }
    Type = 0; return L"";
  }
  
  CString CAoJia::ReadStringL(LONG PID, LONG Hwnd, LONGLONG AddrL, LONG Len, LONG Flag, LONG& Type) {
    CComVariant vType;
    COleVariant v[6]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vType; v[1] = COleVariant(Flag); v[2] = COleVariant(Len); v[3] = COleVariant(AddrL);
    v[4] = COleVariant(Hwnd); v[5] = COleVariant(PID);
    LPCWSTR FunName = L"ReadStringL"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.lVal; return CString(rt.bstrVal);
    }
    Type = 0; return L"";
  }
  
  LONG CAoJia::WriteStringS(LONG PID, LONG Hwnd, LPCWSTR AddrS, LPCWSTR Str, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant(Str); v[2] = COleVariant(AddrS); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"WriteStringS"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WriteStringL(LONG PID, LONG Hwnd, LONGLONG AddrL, LPCWSTR Str, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant(Str); v[2] = COleVariant(AddrL); v[3] = COleVariant(Hwnd); v[4] = COleVariant(PID);
    LPCWSTR FunName = L"WriteStringL"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::FindData(LONG PID, LONG Hwnd, LPCWSTR AddrS, LPCWSTR Data, LONG Step, LONG Type, LONG PN, LONG TN, LPCWSTR FN) {
    COleVariant v[9]; v[0] = COleVariant(FN); v[1] = COleVariant(TN); v[2] = COleVariant(PN); v[3] = COleVariant(Type); v[4] = COleVariant(Step);
    v[5] = COleVariant(Data); v[6] = COleVariant(AddrS); v[7] = COleVariant(Hwnd); v[8] = COleVariant(PID);
    LPCWSTR FunName = L"FindData"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::FindDouble(LONG PID, LONG Hwnd, LPCWSTR AddrS, DOUBLE DbMin, DOUBLE DbMax, LONG Step, LONG Type, LONG PN, LONG TN, LPCWSTR FN) {
    COleVariant v[10]; v[0] = COleVariant(FN); v[1] = COleVariant(TN); v[2] = COleVariant(PN); v[3] = COleVariant(Type); v[4] = COleVariant(Step);
    v[5] = COleVariant(DbMax); v[6] = COleVariant(DbMin); v[7] = COleVariant(AddrS); v[8] = COleVariant(Hwnd); v[9] = COleVariant(PID);
    LPCWSTR FunName = L"FindDouble"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::FindFloat(LONG PID, LONG Hwnd, LPCWSTR AddrS, FLOAT FlMin, FLOAT FlMax, LONG Step, LONG Type, LONG PN, LONG TN, LPCWSTR FN) {
    COleVariant v[10]; v[0] = COleVariant(FN); v[1] = COleVariant(TN); v[2] = COleVariant(PN); v[3] = COleVariant(Type); v[4] = COleVariant(Step);
    v[5] = COleVariant(FlMax); v[6] = COleVariant(FlMin); v[7] = COleVariant(AddrS); v[8] = COleVariant(Hwnd); v[9] = COleVariant(PID);
    LPCWSTR FunName = L"FindFloat"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::FindInt(LONG PID, LONG Hwnd, LPCWSTR AddrS, LONGLONG LlMin, LONGLONG LlMax, LONG Flag, LONG Step, LONG Type, LONG PN, LONG TN, LPCWSTR FN) {
    COleVariant v[11]; v[0] = COleVariant(FN); v[1] = COleVariant(TN); v[2] = COleVariant(PN); v[3] = COleVariant(Type); v[4] = COleVariant(Step);
    v[5] = COleVariant(Flag); v[6] = COleVariant(LlMax); v[7] = COleVariant(LlMin); v[8] = COleVariant(AddrS); v[9] = COleVariant(Hwnd); v[10] = COleVariant(PID);
    LPCWSTR FunName = L"FindInt"; DISPPARAMS dp = { v,NULL,11,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::FindString(LONG PID, LONG Hwnd, LPCWSTR AddrS, LPCWSTR Str, LONG Flag, LONG Nul, LONG Step, LONG Type, LONG PN, LONG TN, LPCWSTR FN) {
    COleVariant v[11]; v[0] = COleVariant(FN); v[1] = COleVariant(TN); v[2] = COleVariant(PN); v[3] = COleVariant(Type); v[4] = COleVariant(Step);
    v[5] = COleVariant(Nul); v[6] = COleVariant(Flag); v[7] = COleVariant(Str); v[8] = COleVariant(AddrS); v[9] = COleVariant(Hwnd); v[10] = COleVariant(PID);
    LPCWSTR FunName = L"FindString"; DISPPARAMS dp = { v,NULL,11,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SuiJi(LONG RMin, LONG RMax) {
    COleVariant v[2]; v[0] = COleVariant(RMax); v[1] = COleVariant(RMin);
    LPCWSTR FunName = L"SuiJi"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GaiLu(LONG P) {
    COleVariant v[1]; v[0] = COleVariant(P);
    LPCWSTR FunName = L"GaiLu"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::YanShi(LONG RMin, LONG RMax) {
    COleVariant v[2]; v[0] = COleVariant(RMax); v[1] = COleVariant(RMin);
    LPCWSTR FunName = L"YanShi"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetClipboard() {
    LPCWSTR FunName = L"GetClipboard"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SetClipboard(LPCWSTR Str) {
    COleVariant v[1]; v[0] = COleVariant(Str);
    LPCWSTR FunName = L"SetClipboard"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetCPU(CString& Type, CString& CPUID) {
    CComVariant vType, vCPUID;
    COleVariant v[2]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vCPUID; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vType;
    LPCWSTR FunName = L"GetCPU"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Type = vType.bstrVal; CPUID = vCPUID.bstrVal; return rt.lVal;
    }
    Type = L""; CPUID = L""; return 0;
  }
  
  LONG CAoJia::GetCPURate() {
    LPCWSTR FunName = L"GetCPURate"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetAero(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetAero"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::Beep(LONG Hz, LONG T) {
    COleVariant v[2]; v[0] = COleVariant(T); v[1] = COleVariant(Hz);
    LPCWSTR FunName = L"Beep"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::Msg(LONG x, LONG y, LPCWSTR Color, LPCWSTR BkColor, LPCWSTR FmColor, LPCWSTR Text, LONG T) {
    COleVariant v[7]; v[0] = COleVariant(T); v[1] = COleVariant(Text); v[2] = COleVariant(FmColor); v[3] = COleVariant(BkColor); v[4] = COleVariant(Color);
    v[5] = COleVariant(y); v[6] = COleVariant(x);
    LPCWSTR FunName = L"Msg"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetFontSmoothing() {
    LPCWSTR FunName = L"GetFontSmoothing"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::SetFontSmoothing(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetFontSmoothing"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetUAC() {
    LPCWSTR FunName = L"GetUAC"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::SetUAC(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetUAC"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetBeep() {
    LPCWSTR FunName = L"GetBeep"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::SetBeep(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetBeep"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetPower(LONG VT, LONG ST) {
    COleVariant v[2]; v[0] = COleVariant(ST); v[1] = COleVariant(VT);
    LPCWSTR FunName = L"SetPower"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetPowerState(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetPowerState"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetPower(LONG& VT, LONG& ST) {
    CComVariant vVT, vST;
    COleVariant v[2]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vST; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vVT;
    LPCWSTR FunName = L"GetPower"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      VT = vVT.lVal; ST = vST.lVal; return rt.lVal;
    }
    VT = -1; ST = -1; return -1;
  }
  
  LONG CAoJia::SetScreenSave(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetScreenSave"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::ExitOs(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"ExitOs"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  ULONG CAoJia::GetTime() {
    LPCWSTR FunName = L"GetTime"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetScreen(LONG& Width, LONG& Height) {
    CComVariant vWidth, vHeight;
    COleVariant v[2]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vHeight; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vWidth;
    LPCWSTR FunName = L"GetScreen"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Width = vWidth.lVal; Height = vHeight.lVal; return rt.lVal;
    }
    Width = 0; Height = 0; return 0;
  }
  
  LONG CAoJia::SetScreen(LONG Width, LONG Height) {
    COleVariant v[2]; v[0] = COleVariant(Height); v[1] = COleVariant(Width);
    LPCWSTR FunName = L"SetScreen"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetMemory(LONG& TPhy, DOUBLE& APhy) {
    CComVariant vTPhy, vAPhy;
    COleVariant v[2]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vAPhy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vTPhy;
    LPCWSTR FunName = L"GetMemory"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      TPhy = vTPhy.lVal; APhy = vAPhy.dblVal; return rt.lVal;
    }
    TPhy = -1; APhy = -1.0; return -1;
  }
  
  LONG CAoJia::GetDPI() {
    LPCWSTR FunName = L"GetDPI"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::Cmd(LPCWSTR CL, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(CL);
    LPCWSTR FunName = L"Cmd"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetGc() {
    LPCWSTR FunName = L"GetGc"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::GetDisk(CString& Model, CString& Revision) {
    CComVariant vModel, vRevision;
    COleVariant v[2]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vRevision; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vModel;
    LPCWSTR FunName = L"GetDisk"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Model = vModel.bstrVal; Revision = vRevision.bstrVal; return CString(rt.bstrVal);
    }
    Model = L""; Revision = L""; return L"";
  }
  
  LONG CAoJia::PlayMusic(LPCWSTR MF) {
    COleVariant v[1]; v[0] = COleVariant(MF);
    LPCWSTR FunName = L"PlayMusic"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::StopMusic() {
    LPCWSTR FunName = L"StopMusic"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::RunApp(LPCWSTR Path, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Path);
    LPCWSTR FunName = L"RunApp"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::SuiJiMZ(LONG MN, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(MN);
    LPCWSTR FunName = L"SuiJiMZ"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::GetSystemTime() {
    LPCWSTR FunName = L"GetSystemTime"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SetSystemTime(LPCWSTR ST) {
    COleVariant v[1]; v[0] = COleVariant(ST);
    LPCWSTR FunName = L"SetSystemTime"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::GetDiskSize() {
    LPCWSTR FunName = L"GetDiskSize"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::GetScreenS(LONG& xS, LONG& yS) {
    CComVariant vxS, vyS;
    COleVariant v[2]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vyS; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vxS;
    LPCWSTR FunName = L"GetScreenS"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      xS = vxS.lVal; yS = vyS.lVal; return CString(rt.bstrVal);
    }
    xS = 0; yS = 0; return L"";
  }
  
  CString CAoJia::GetMAC() {
    LPCWSTR FunName = L"GetMAC"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::KeyDown(USHORT KeyD) {
    COleVariant v[1]; v[0] = COleVariant((LONG)KeyD);
    LPCWSTR FunName = L"KeyDown"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyUp(USHORT KeyD) {
    COleVariant v[1]; v[0] = COleVariant((LONG)KeyD);
    LPCWSTR FunName = L"KeyUp"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyPress(USHORT KeyD) {
    COleVariant v[1]; v[0] = COleVariant((LONG)KeyD);
    LPCWSTR FunName = L"KeyPress"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyDownS(LPCWSTR KeyDS) {
    COleVariant v[1]; v[0] = COleVariant(KeyDS);
    LPCWSTR FunName = L"KeyDownS"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyUpS(LPCWSTR KeyDS) {
    COleVariant v[1]; v[0] = COleVariant(KeyDS);
    LPCWSTR FunName = L"KeyUpS"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyPressS(LPCWSTR KeyDS) {
    COleVariant v[1]; v[0] = COleVariant(KeyDS);
    LPCWSTR FunName = L"KeyPressS"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyPressD(USHORT KeyD, LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[5]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin); v[4] = COleVariant((LONG)KeyD);
    LPCWSTR FunName = L"KeyPressD"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyPressSD(LPCWSTR KeyDS, LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[5]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin); v[4] = COleVariant(KeyDS);
    LPCWSTR FunName = L"KeyPressSD"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KeyPressZ(LPCWSTR KeyZ, LONG RMin, LONG RMax) {
    COleVariant v[3]; v[0] = COleVariant(RMax); v[1] = COleVariant(RMin); v[2] = COleVariant(KeyZ);
    LPCWSTR FunName = L"KeyPressZ"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetKeyDState(LONG KeyD) {
    COleVariant v[1]; v[0] = COleVariant(KeyD);
    LPCWSTR FunName = L"GetKeyDState"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::WaitKeyD(LONG KeyD, LONG TKeyD) {
    COleVariant v[2]; v[0] = COleVariant(TKeyD); v[1] = COleVariant(KeyD);
    LPCWSTR FunName = L"WaitKeyD"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::LeftDown() {
    LPCWSTR FunName = L"LeftDown"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LeftUp() {
    LPCWSTR FunName = L"LeftUp"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::RightDown() {
    LPCWSTR FunName = L"RightDown"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::RightUp() {
    LPCWSTR FunName = L"RightUp"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MiddleDown() {
    LPCWSTR FunName = L"MiddleDown"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MiddleUp() {
    LPCWSTR FunName = L"MiddleUp"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WheelDown() {
    LPCWSTR FunName = L"WheelDown"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WheelUp() {
    LPCWSTR FunName = L"WheelUp"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LeftClick() {
    LPCWSTR FunName = L"LeftClick"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::RightClick() {
    LPCWSTR FunName = L"RightClick"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MiddleClick() {
    LPCWSTR FunName = L"MiddleClick"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LeftClickD(LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[4]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin);
    LPCWSTR FunName = L"LeftClickD"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::RightClickD(LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[4]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin);
    LPCWSTR FunName = L"RightClickD"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MiddleClickD(LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[4]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin);
    LPCWSTR FunName = L"MiddleClickD"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WheelDownD(LONG Num, LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[5]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin); v[4] = COleVariant(Num);
    LPCWSTR FunName = L"WheelDownD"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::WheelUpD(LONG Num, LONG RMin, LONG RMax, LONG RDMin, LONG RDMax) {
    COleVariant v[5]; v[0] = COleVariant(RDMax); v[1] = COleVariant(RDMin); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin); v[4] = COleVariant(Num);
    LPCWSTR FunName = L"WheelUpD"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LeftDoubleClick() {
    LPCWSTR FunName = L"LeftDoubleClick"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LeftDoubleClickD(LONG RMin, LONG RMax, LONG RDMin, LONG RDMax, LONG RDRMin, LONG RDRMax) {
    COleVariant v[6]; v[0] = COleVariant(RDRMax); v[1] = COleVariant(RDRMin); v[2] = COleVariant(RDMax); v[3] = COleVariant(RDMin); v[4] = COleVariant(RMax);
    v[5] = COleVariant(RMin);
    LPCWSTR FunName = L"LeftDoubleClickD"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::RightDoubleClickD(LONG RMin, LONG RMax, LONG RDMin, LONG RDMax, LONG RDRMin, LONG RDRMax) {
    COleVariant v[6]; v[0] = COleVariant(RDRMax); v[1] = COleVariant(RDRMin); v[2] = COleVariant(RDMax); v[3] = COleVariant(RDMin); v[4] = COleVariant(RMax);
    v[5] = COleVariant(RMin);
    LPCWSTR FunName = L"RightDoubleClickD"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MiddleDoubleClickD(LONG RMin, LONG RMax, LONG RDMin, LONG RDMax, LONG RDRMin, LONG RDRMax) {
    COleVariant v[6]; v[0] = COleVariant(RDRMax); v[1] = COleVariant(RDRMin); v[2] = COleVariant(RDMax); v[3] = COleVariant(RDMin); v[4] = COleVariant(RMax);
    v[5] = COleVariant(RMin);
    LPCWSTR FunName = L"MiddleDoubleClickD"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetDoubleClickTime() {
    LPCWSTR FunName = L"GetDoubleClickTime"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetDoubleClickTime(LONG T) {
    COleVariant v[1]; v[0] = COleVariant(T);
    LPCWSTR FunName = L"SetDoubleClickTime"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetMouseAccuracy(LONG MouseA) {
    COleVariant v[1]; v[0] = COleVariant(MouseA);
    LPCWSTR FunName = L"SetMouseAccuracy"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetMouseSpeed(LONG MouseS) {
    COleVariant v[1]; v[0] = COleVariant(MouseS);
    LPCWSTR FunName = L"SetMouseSpeed"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetMouseSpeed() {
    LPCWSTR FunName = L"GetMouseSpeed"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveTo(LONG x, LONG y) {
    COleVariant v[2]; v[0] = COleVariant(y); v[1] = COleVariant(x);
    LPCWSTR FunName = L"MoveTo"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveR(LONG Rx, LONG Ry) {
    COleVariant v[2]; v[0] = COleVariant(Ry); v[1] = COleVariant(Rx);
    LPCWSTR FunName = L"MoveR"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveToD(LONG x, LONG y, LONG xRMin, LONG xRMax, LONG yRMin, LONG yRMax, LONG RMin, LONG RMax, LONG Speed) {
    COleVariant v[9]; v[0] = COleVariant(Speed); v[1] = COleVariant(RMax); v[2] = COleVariant(RMin); v[3] = COleVariant(yRMax); v[4] = COleVariant(yRMin);
    v[5] = COleVariant(xRMax); v[6] = COleVariant(xRMin); v[7] = COleVariant(y); v[8] = COleVariant(x);
    LPCWSTR FunName = L"MoveToD"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveRD(LONG Rx, LONG Ry, LONG xRMin, LONG xRMax, LONG yRMin, LONG yRMax, LONG RMin, LONG RMax, LONG Speed) {
    COleVariant v[9]; v[0] = COleVariant(Speed); v[1] = COleVariant(RMax); v[2] = COleVariant(RMin); v[3] = COleVariant(yRMax); v[4] = COleVariant(yRMin);
    v[5] = COleVariant(xRMax); v[6] = COleVariant(xRMin); v[7] = COleVariant(Ry); v[8] = COleVariant(Rx);
    LPCWSTR FunName = L"MoveRD"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveToQ(LONG x, LONG y, LONG xRMin, LONG xRMax, LONG yRMin, LONG yRMax, LONG RMin, LONG RMax, LONG Speed) {
    COleVariant v[9]; v[0] = COleVariant(Speed); v[1] = COleVariant(RMax); v[2] = COleVariant(RMin); v[3] = COleVariant(yRMax); v[4] = COleVariant(yRMin);
    v[5] = COleVariant(xRMax); v[6] = COleVariant(xRMin); v[7] = COleVariant(y); v[8] = COleVariant(x);
    LPCWSTR FunName = L"MoveToQ"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::MoveRQ(LONG Rx, LONG Ry, LONG xRMin, LONG xRMax, LONG yRMin, LONG yRMax, LONG RMin, LONG RMax, LONG Speed) {
    COleVariant v[9]; v[0] = COleVariant(Speed); v[1] = COleVariant(RMax); v[2] = COleVariant(RMin); v[3] = COleVariant(yRMax); v[4] = COleVariant(yRMin);
    v[5] = COleVariant(xRMax); v[6] = COleVariant(xRMin); v[7] = COleVariant(Ry); v[8] = COleVariant(Rx);
    LPCWSTR FunName = L"MoveRQ"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetMousePos(LONG& x, LONG& y, LONG Type) {
    CComVariant vx, vy;
    COleVariant v[3]; v[0] = COleVariant(Type); v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vy; v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vx;
    LPCWSTR FunName = L"GetMousePos"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    x = -1; y = -1; return 0;
  }
  
  LONG CAoJia::SetMousePos(LONG Sx1, LONG Sy1, LONG Sx2, LONG Sy2, LONG SDxy, LONG Dx1, LONG Dy1, LONG Dx2, LONG Dy2, LONG RMin, LONG RMax, LONG Speed, LONG Type) {
    COleVariant v[13]; v[0] = COleVariant(Type); v[1] = COleVariant(Speed); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin); v[4] = COleVariant(Dy2);
    v[5] = COleVariant(Dx2); v[6] = COleVariant(Dy1); v[7] = COleVariant(Dx1); v[8] = COleVariant(SDxy); v[9] = COleVariant(Sy2); v[10] = COleVariant(Sx2);
    v[11] = COleVariant(Sy1); v[12] = COleVariant(Sx1);
    LPCWSTR FunName = L"SetMousePos"; DISPPARAMS dp = { v,NULL,13,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetMouseHotspot(LONG& x, LONG& y, LONG Type) {
    CComVariant vx, vy;
    COleVariant v[3]; v[0] = COleVariant(Type); v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vy; v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vx;
    LPCWSTR FunName = L"GetMouseHotspot"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    x = -1; y = -1; return 0;
  }
  
  CString CAoJia::GetMouseShape(LONG Type, LONG Flag) {
    COleVariant v[2]; v[0] = COleVariant(Flag); v[1] = COleVariant(Type);
    LPCWSTR FunName = L"GetMouseShape"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::SendString(LONG Hwnd, LPCWSTR Str, LONG RMin, LONG RMax, LONG Type, LONG Flag) {
    COleVariant v[6]; v[0] = COleVariant(Flag); v[1] = COleVariant(Type); v[2] = COleVariant(RMax); v[3] = COleVariant(RMin); v[4] = COleVariant(Str);
    v[5] = COleVariant(Hwnd);
    LPCWSTR FunName = L"SendString"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::BlockInput(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"BlockInput"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::OpenURL(LPCWSTR URL) {
    COleVariant v[1]; v[0] = COleVariant(URL);
    LPCWSTR FunName = L"OpenURL"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DownloadFile(LPCWSTR URL, LPCWSTR FN, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(FN); v[2] = COleVariant(URL);
    LPCWSTR FunName = L"DownloadFile"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetDownloadState() {
    LPCWSTR FunName = L"GetDownloadState"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::KQHouTai(LONG Hwnd, LPCWSTR Screen, LPCWSTR Keyboard, LPCWSTR Mouse, LPCWSTR Flag, LONG Type) {
    COleVariant v[6]; v[0] = COleVariant(Type); v[1] = COleVariant(Flag); v[2] = COleVariant(Mouse); v[3] = COleVariant(Keyboard); v[4] = COleVariant(Screen);
    v[5] = COleVariant(Hwnd);
    LPCWSTR FunName = L"KQHouTai"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GBHouTai() {
    LPCWSTR FunName = L"GBHouTai"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetHwndSKM(LONG HwndS, LONG HwndK, LONG HwndM) {
    COleVariant v[3]; v[0] = COleVariant(HwndM); v[1] = COleVariant(HwndK); v[2] = COleVariant(HwndS);
    LPCWSTR FunName = L"SetHwndSKM"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetWindowSNA(LONG SNA) {
    COleVariant v[1]; v[0] = COleVariant(SNA);
    LPCWSTR FunName = L"SetWindowSNA"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetKMSync(LONG Keyboard, ULONG uToK, LONG Mouse, ULONG uToM) {
    COleVariant v[4]; v[0] = COleVariant((ULONGLONG)uToM); v[1] = COleVariant(Mouse); v[2] = COleVariant((ULONGLONG)uToK); v[3] = COleVariant(Keyboard);
    LPCWSTR FunName = L"SetKMSync"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetIme(LONG Type) {
    COleVariant v[1]; v[0] = COleVariant(Type);
    LPCWSTR FunName = L"SetIme"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetKMLock(LONG LockK, LONG LockM) {
    COleVariant v[2]; v[0] = COleVariant(LockM); v[1] = COleVariant(LockK);
    LPCWSTR FunName = L"SetKMLock"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetTimeS(ULONG TimeS) {
    COleVariant v[1]; v[0] = COleVariant((ULONGLONG)TimeS);
    LPCWSTR FunName = L"SetTimeS"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::DownCpu(ULONG DCpuT, LONG DCpuD) {
    COleVariant v[2]; v[0] = COleVariant(DCpuD); v[1] = COleVariant((ULONGLONG)DCpuT);
    LPCWSTR FunName = L"DownCpu"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LockScreen(LONG LockS) {
    COleVariant v[1]; v[0] = COleVariant(LockS);
    LPCWSTR FunName = L"LockScreen"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetFPS() {
    LPCWSTR FunName = L"GetFPS"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::FindShape(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR ColorP, LONG Dir, DOUBLE SimP, DOUBLE SimD, LONG& x, LONG& y) {
    CComVariant vx, vy;
    COleVariant v[10]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx; v[2] = COleVariant(SimD);
    v[3] = COleVariant(SimP); v[4] = COleVariant(Dir); v[5] = COleVariant(ColorP); v[6] = COleVariant(y2); v[7] = COleVariant(x2); v[8] = COleVariant(y1);
    v[9] = COleVariant(x1);
    LPCWSTR FunName = L"FindShape"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    x = -1; y = -1; return 0;
  }
  
  CString CAoJia::FindShapeEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR ColorP, LONG Dir, DOUBLE SimP, DOUBLE SimD) {
    COleVariant v[8]; v[0] = COleVariant(SimD); v[1] = COleVariant(SimP); v[2] = COleVariant(Dir); v[3] = COleVariant(ColorP); v[4] = COleVariant(y2);
    v[5] = COleVariant(x2); v[6] = COleVariant(y1); v[7] = COleVariant(x1);
    LPCWSTR FunName = L"FindShapeEx"; DISPPARAMS dp = { v,NULL,8,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::FindColorSquEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, DOUBLE Sim, DOUBLE SimD, LONG Dir, LONG Width, LONG Height) {
    COleVariant v[10]; v[0] = COleVariant(Height); v[1] = COleVariant(Width); v[2] = COleVariant(Dir); v[3] = COleVariant(SimD); v[4] = COleVariant(Sim);
    v[5] = COleVariant(Color); v[6] = COleVariant(y2); v[7] = COleVariant(x2); v[8] = COleVariant(y1); v[9] = COleVariant(x1);
    LPCWSTR FunName = L"FindColorSquEx"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FindColorSqu(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, DOUBLE Sim, DOUBLE SimD, LONG Dir, LONG Width, LONG Height, LONG& x, LONG& y) {
    CComVariant vx, vy;
    COleVariant v[12]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx; v[2] = COleVariant(Height);
    v[3] = COleVariant(Width); v[4] = COleVariant(Dir); v[5] = COleVariant(SimD); v[6] = COleVariant(Sim); v[7] = COleVariant(Color); v[8] = COleVariant(y2);
    v[9] = COleVariant(x2); v[10] = COleVariant(y1); v[11] = COleVariant(x1);
    LPCWSTR FunName = L"FindColorSqu"; DISPPARAMS dp = { v,NULL,12,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    x = -1; y = -1; return 0;
  }
  
  CString CAoJia::FindPicDEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR PicName, LPCWSTR ColorP, DOUBLE Sim, DOUBLE SimD, LONG Dir, LONG Type, LONG TypeT) {
    COleVariant v[11]; v[0] = COleVariant(TypeT); v[1] = COleVariant(Type); v[2] = COleVariant(Dir); v[3] = COleVariant(SimD); v[4] = COleVariant(Sim);
    v[5] = COleVariant(ColorP); v[6] = COleVariant(PicName); v[7] = COleVariant(y2); v[8] = COleVariant(x2); v[9] = COleVariant(y1); v[10] = COleVariant(x1);
    LPCWSTR FunName = L"FindPicDEx"; DISPPARAMS dp = { v,NULL,11,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FindPicD(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR PicName, LPCWSTR ColorP, DOUBLE Sim, DOUBLE SimD, LONG Dir, LONG Type, CString& Pic, LONG& x, LONG& y) {
    CComVariant vx, vy, vPic;
    COleVariant v[13]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vPic; v[3] = COleVariant(Type); v[4] = COleVariant(Dir); v[5] = COleVariant(SimD); v[6] = COleVariant(Sim);
    v[7] = COleVariant(ColorP); v[8] = COleVariant(PicName); v[9] = COleVariant(y2); v[10] = COleVariant(x2); v[11] = COleVariant(y1); v[12] = COleVariant(x1);
    LPCWSTR FunName = L"FindPicD"; DISPPARAMS dp = { v,NULL,13,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Pic = vPic.bstrVal; x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    Pic = L""; x = -1; y = -1; return -1;
  }
  
  CString CAoJia::FindPicEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR PicName, LPCWSTR ColorP, DOUBLE Sim, LONG Dir, LONG Type, LONG TypeT) {
    COleVariant v[10]; v[0] = COleVariant(TypeT); v[1] = COleVariant(Type); v[2] = COleVariant(Dir); v[3] = COleVariant(Sim);
    v[4] = COleVariant(ColorP); v[5] = COleVariant(PicName); v[6] = COleVariant(y2); v[7] = COleVariant(x2); v[8] = COleVariant(y1); v[9] = COleVariant(x1);
    LPCWSTR FunName = L"FindPicEx"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FindPic(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR PicName, LPCWSTR ColorP, DOUBLE Sim, LONG Dir, LONG Type, CString& Pic, LONG& x, LONG& y) {
    CComVariant vx, vy, vPic;
    COleVariant v[12]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vPic; v[3] = COleVariant(Type); v[4] = COleVariant(Dir); v[5] = COleVariant(Sim);
    v[6] = COleVariant(ColorP); v[7] = COleVariant(PicName); v[8] = COleVariant(y2); v[9] = COleVariant(x2); v[10] = COleVariant(y1); v[11] = COleVariant(x1);
    LPCWSTR FunName = L"FindPic"; DISPPARAMS dp = { v,NULL,12,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      Pic = vPic.bstrVal; x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    Pic = L""; x = -1; y = -1; return -1;
  }
  
  CString CAoJia::FindMultiColorEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, LPCWSTR ColorP, DOUBLE Sim, LONG Dir, DOUBLE SimP, DOUBLE SimD) {
    COleVariant v[10]; v[0] = COleVariant(SimD); v[1] = COleVariant(SimP); v[2] = COleVariant(Dir); v[3] = COleVariant(Sim);
    v[4] = COleVariant(ColorP); v[5] = COleVariant(Color); v[6] = COleVariant(y2); v[7] = COleVariant(x2); v[8] = COleVariant(y1); v[9] = COleVariant(x1);
    LPCWSTR FunName = L"FindMultiColorEx"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FindMultiColor(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, LPCWSTR ColorP, DOUBLE Sim, LONG Dir, DOUBLE SimP, DOUBLE SimD, LONG& x, LONG& y) {
    CComVariant vx, vy;
    COleVariant v[12]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx; v[2] = COleVariant(SimD);
    v[3] = COleVariant(SimP); v[4] = COleVariant(Dir); v[5] = COleVariant(Sim); v[6] = COleVariant(ColorP); v[7] = COleVariant(Color); v[8] = COleVariant(y2);
    v[9] = COleVariant(x2); v[10] = COleVariant(y1); v[11] = COleVariant(x1);
    LPCWSTR FunName = L"FindMultiColor"; DISPPARAMS dp = { v,NULL,12,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    x = -1; y = -1; return -1;
  }
  
  CString CAoJia::FindColorEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, DOUBLE Sim, LONG Dir) {
    COleVariant v[7]; v[0] = COleVariant(Dir); v[1] = COleVariant(Sim);
    v[2] = COleVariant(Color); v[3] = COleVariant(y2); v[4] = COleVariant(x2); v[5] = COleVariant(y1); v[6] = COleVariant(x1);
    LPCWSTR FunName = L"FindColorEx"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FindColor(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, DOUBLE Sim, LONG Dir, LONG& x, LONG& y) {
    CComVariant vx, vy;
    COleVariant v[9]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx;
    v[2] = COleVariant(Dir); v[3] = COleVariant(Sim); v[4] = COleVariant(Color); v[5] = COleVariant(y2);
    v[6] = COleVariant(x2); v[7] = COleVariant(y1); v[8] = COleVariant(x1);
    LPCWSTR FunName = L"FindColor"; DISPPARAMS dp = { v,NULL,9,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    x = -1; y = -1; return -1;
  }
  
  LONG CAoJia::FindColorM(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, DOUBLE Sim, LONG Count) {
    COleVariant v[7]; v[0] = COleVariant(Count); v[1] = COleVariant(Sim); v[2] = COleVariant(Color); v[3] = COleVariant(y2);
    v[4] = COleVariant(x2); v[5] = COleVariant(y1); v[6] = COleVariant(x1);
    LPCWSTR FunName = L"FindColorM"; DISPPARAMS dp = { v,NULL,7,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetColorNum(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Color, DOUBLE Sim) {
    COleVariant v[6]; v[0] = COleVariant(Sim); v[1] = COleVariant(Color); v[2] = COleVariant(y2);
    v[3] = COleVariant(x2); v[4] = COleVariant(y1); v[5] = COleVariant(x1);
    LPCWSTR FunName = L"GetColorNum"; DISPPARAMS dp = { v,NULL,6,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  VARIANT CAoJia::GetColorAve(LONG x1, LONG y1, LONG x2, LONG y2, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant(y2); v[2] = COleVariant(x2); v[3] = COleVariant(y1); v[4] = COleVariant(x1);
    LPCWSTR FunName = L"GetColorAve"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt;
    }
    rt.vt = VT_I4; rt.lVal = -1; return rt;
  }
  
  LONG CAoJia::CmpColor(LONG x, LONG y, LPCWSTR Color, DOUBLE Sim, LONG Type) {
    COleVariant v[5]; v[0] = COleVariant(Type); v[1] = COleVariant(Sim); v[2] = COleVariant(Color); v[3] = COleVariant(y); v[4] = COleVariant(x);
    LPCWSTR FunName = L"CmpColor"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  VARIANT CAoJia::GetColor(LONG x, LONG y, LONG Type, LONG TypeD) {
    COleVariant v[4]; v[0] = COleVariant(TypeD); v[1] = COleVariant(Type); v[2] = COleVariant(y); v[3] = COleVariant(x);
    LPCWSTR FunName = L"GetColor"; DISPPARAMS dp = { v,NULL,4,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt;
    }
    rt.vt = VT_I4; rt.lVal = -1; return rt;
  }
  
  CString CAoJia::BGRorRGB(LPCWSTR Color) {
    COleVariant v[1]; v[0] = COleVariant(Color);
    LPCWSTR FunName = L"BGRorRGB"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::BGRorRGBtoHSV(LPCWSTR Color, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Color);
    LPCWSTR FunName = L"BGRorRGBtoHSV"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  CString CAoJia::HSVtoBGRorRGB(LPCWSTR Color, LONG Type) {
    COleVariant v[2]; v[0] = COleVariant(Type); v[1] = COleVariant(Color);
    LPCWSTR FunName = L"HSVtoBGRorRGB"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::LoadPic(LPCWSTR PicName) {
    COleVariant v[1]; v[0] = COleVariant(PicName);
    LPCWSTR FunName = L"LoadPic"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::FreePic(LPCWSTR PicName) {
    COleVariant v[1]; v[0] = COleVariant(PicName);
    LPCWSTR FunName = L"FreePic"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::IsScreenStuck(LONG x1, LONG y1, LONG x2, LONG y2, LONG T) {
    COleVariant v[5]; v[0] = COleVariant(T); v[1] = COleVariant(y2); v[2] = COleVariant(x2); v[3] = COleVariant(y1); v[4] = COleVariant(x1);
    LPCWSTR FunName = L"IsScreenStuck"; DISPPARAMS dp = { v,NULL,5,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::GetPicSize(LPCWSTR PicName, LONG& PicW, LONG& PicH) {
    CComVariant vPicW, vPicH;
    COleVariant v[3]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vPicH; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vPicW; v[2] = COleVariant(PicName);
    LPCWSTR FunName = L"GetPicSize"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      PicW = vPicW.lVal; PicH = vPicH.lVal; return rt.lVal;
    }
    PicW = -1; PicH = -1; return 0;
  }
  
  LONG CAoJia::PicToBmp(LPCWSTR PicName, LPCWSTR BmpName) {
    COleVariant v[2]; v[0] = COleVariant(BmpName); v[1] = COleVariant(PicName);
    LPCWSTR FunName = L"PicToBmp"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::ScreenShot(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR PicName, LONG Type, LONG Quality, ULONG TD, ULONG T, LONG Flag, LONG Mouse) {
    COleVariant v[11]; v[0] = COleVariant(Mouse); v[1] = COleVariant(Flag); v[2] = COleVariant((ULONGLONG)T); v[3] = COleVariant((ULONGLONG)TD);
    v[4] = COleVariant(Quality); v[5] = COleVariant(Type); v[6] = COleVariant(PicName); v[7] = COleVariant(y2); v[8] = COleVariant(x2);
    v[9] = COleVariant(y1); v[10] = COleVariant(x1);
    LPCWSTR FunName = L"ScreenShot"; DISPPARAMS dp = { v,NULL,11,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::LoadDict(LONG DNum, LPCWSTR DName) {
    COleVariant v[2]; v[0] = COleVariant(DName); v[1] = COleVariant(DNum);
    LPCWSTR FunName = L"LoadDict"; DISPPARAMS dp = { v,NULL,2,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetDict(LONG DNum) {
    COleVariant v[1]; v[0] = COleVariant(DNum);
    LPCWSTR FunName = L"SetDict"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  CString CAoJia::Ocr(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Str, LPCWSTR Color, DOUBLE Sim, LONG TypeC, LONG TypeD, LONG TypeR, LONG TypeT, LPCWSTR HLine, LPCWSTR PicName) {
    COleVariant v[13]; v[0] = COleVariant(PicName); v[1] = COleVariant(HLine); v[2] = COleVariant(TypeT); v[3] = COleVariant(TypeR); v[4] = COleVariant(TypeD);
    v[5] = COleVariant(TypeC); v[6] = COleVariant(Sim); v[7] = COleVariant(Color); v[8] = COleVariant(Str); v[9] = COleVariant(y2); v[10] = COleVariant(x2);
    v[11] = COleVariant(y1); v[12] = COleVariant(x1);
    LPCWSTR FunName = L"Ocr"; DISPPARAMS dp = { v,NULL,13,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }
  
  LONG CAoJia::FindStr(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Str, LPCWSTR Color, DOUBLE Sim, LONG Dir, LONG TypeC, LONG TypeD, CString& StrD, LONG& x, LONG& y) {
    CComVariant vx, vy, vStrD;
    COleVariant v[13]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vStrD; v[3] = COleVariant(TypeD); v[4] = COleVariant(TypeC); v[5] = COleVariant(Dir); v[6] = COleVariant(Sim);
    v[7] = COleVariant(Color); v[8] = COleVariant(Str); v[9] = COleVariant(y2); v[10] = COleVariant(x2); v[11] = COleVariant(y1); v[12] = COleVariant(x1);
    LPCWSTR FunName = L"FindStr"; DISPPARAMS dp = { v,NULL,13,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      StrD = vStrD.bstrVal; x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    StrD = L""; x = -1; y = -1; return -1;
  }
  
  LONG CAoJia::FreeDict(LONG DNum) {
    COleVariant v[1]; v[0] = COleVariant(DNum);
    LPCWSTR FunName = L"FreeDict"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::GetDict(LONG GD, LONG DNum, LONG Type) {
    COleVariant v[3]; v[0] = COleVariant(Type); v[1] = COleVariant(DNum); v[2] = COleVariant(GD);
    LPCWSTR FunName = L"GetDict"; DISPPARAMS dp = { v,NULL,3,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return -1;
  }
  
  LONG CAoJia::SetDictWidth(LONG DW) {
    COleVariant v[1]; v[0] = COleVariant(DW);
    LPCWSTR FunName = L"SetDictWidth"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::SetDictHeight(LONG DH) {
    COleVariant v[1]; v[0] = COleVariant(DH);
    LPCWSTR FunName = L"SetDictHeight"; DISPPARAMS dp = { v,NULL,1,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }
  
  LONG CAoJia::FindStrM(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Str, LPCWSTR Color, DOUBLE Sim, LONG TypeC, LONG TypeD, CString& StrD, LONG& x, LONG& y) {
    CComVariant vx, vy, vStrD;
    COleVariant v[12]; v[0].vt = VT_BYREF | VT_VARIANT; v[0].pvarVal = &vy; v[1].vt = VT_BYREF | VT_VARIANT; v[1].pvarVal = &vx;
    v[2].vt = VT_BYREF | VT_VARIANT; v[2].pvarVal = &vStrD; v[3] = COleVariant(TypeD); v[4] = COleVariant(TypeC); v[5] = COleVariant(Sim);
    v[6] = COleVariant(Color); v[7] = COleVariant(Str); v[8] = COleVariant(y2); v[9] = COleVariant(x2); v[10] = COleVariant(y1); v[11] = COleVariant(x1);
    LPCWSTR FunName = L"FindStrM"; DISPPARAMS dp = { v,NULL,12,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      StrD = vStrD.bstrVal; x = vx.lVal; y = vy.lVal; return rt.lVal;
    }
    StrD = L""; x = -1; y = -1; return -1;
  }
  
  CString CAoJia::FindStrMEx(LONG x1, LONG y1, LONG x2, LONG y2, LPCWSTR Str, LPCWSTR Color, DOUBLE Sim, LONG TypeC, LONG TypeD, LPCWSTR HLine) {
    COleVariant v[10]; v[0] = COleVariant(HLine); v[1] = COleVariant(TypeD); v[2] = COleVariant(TypeC); v[3] = COleVariant(Sim); v[4] = COleVariant(Color);
    v[5] = COleVariant(Str); v[6] = COleVariant(y2); v[7] = COleVariant(x2); v[8] = COleVariant(y1); v[9] = COleVariant(x1);
    LPCWSTR FunName = L"FindStrMEx"; DISPPARAMS dp = { v,NULL,10,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return CString(rt.bstrVal);
    }
    return L"";
  }

  LONG CAoJia::SetParam64ToAddr() {
    LPCWSTR FunName = L"SetParam64ToAddr"; DISPPARAMS dp = { NULL,NULL,0,0 }; CComVariant rt; static DISPID DispId = -1;
    if (SUCCEEDED(Call(FunName, &DispId, &dp, &rt))) {
      return rt.lVal;
    }
    return 0;
  }


int main() {
  CoInitializeEx(NULL, COINIT_APARTMENTTHREADED); CString Str; CStringA SA; LONG AJD;
  //下面的代码中ARegJ64.dll和AoJia64.dll的路径要换成你自己的,如果是32位运行环境,插件名和插件路径都要改成32位的
  CAoJia AJ(L"C:\\Users\\Administrator\\Desktop\\work\\ajdll\\ARegJ64.dll", L"C:\\Users\\Administrator\\Desktop\\work\\ajdll\\AoJia64.dll");

  //或者像下面这样写,这种写法不用每次创建对象都调用CARegJ类的函数SetDllPathW,当然每次都调用也不会有问题
  //CARegJ::SetDllPathW(L"C:\\Users\\Administrator\\Desktop\\AJ64\\ARegJ64.dll", L"C:\\Users\\Administrator\\Desktop\\AJ64\\AoJia64.dll");
  //CAoJia AJ;

  if (AJ.hr == S_OK) {
    SA = AJ.VerS(); cout << "版本号: " << SA << endl;
    SA = AJ.GetModulePath(0, 0, L"AoJia64.dll", 0); cout << "插件路径: " << SA << endl;
  }
  else {
    Str.Format(L"%08X", AJ.hr); MessageBoxW(NULL, L"创建对象失败,返回的错误码是: " + Str, L"错误", MB_SETFOREGROUND);
  }
  CoUninitialize(); return 0;
}
