unit main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, process, Forms, Controls, Graphics, Dialogs, StdCtrls,
  ExtCtrls, ComCtrls, Buttons, UTF8Process, setup;

type

  { TForm1 }

  TForm1 = class(TForm)
    BitBtn1: TBitBtn;
    Camera: TImage;
    OpenButton: TButton;
    Process1: TProcess;
    RandomButton: TButton;
    StartButton: TButton;
    StatusBar1: TStatusBar;
    StopButton: TButton;
    Timer1: TTimer;
    procedure BitBtn1Click(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure OpenButtonClick(Sender: TObject);
    procedure Timer1Timer(Sender: TObject);
  private
    camera_busy : Boolean;
  public

  end;

var
  Form1: TForm1;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.OpenButtonClick(Sender: TObject);
begin

end;

procedure TForm1.Timer1Timer(Sender: TObject);
var
jpg: TJPEGImage;
begin

  Process1.CommandLine := 'fswebcam -r 640x480 /tmp/wp_rubkiks_camera.jpg';
  Process1.Execute;

  jpg := TJPEGImage.Create;
  jpg.LoadFromFile('/tmp/wp_rubkiks_camera.jpg');

  Camera.Picture.Assign(jpg);

  jpg.Free;

end;

procedure TForm1.BitBtn1Click(Sender: TObject);
begin
  SetupForm.show();
end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  //camera_busy = false;
end;

end.

