package main;

import java.awt.Canvas;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Graphics;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.image.BufferStrategy;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import javax.swing.JFrame;

import object.Ball;
import object.Robot;
import object.Object;
import screen.Configura;

public class Simulator extends Canvas implements Runnable, KeyListener, MouseListener{
		
	private static final long serialVersionUID = 1L;
	public static JFrame frame;
	public static JFrame con;
	private Thread thread;
	private boolean isRunning = true;
	public static final int WIDTH = 1215;
	public static final int HEIGHT = 910;
	public static final int WIDTH_ = 410;
	public static final int HEIGHT_ = 610;
    public static int FPS;
    public static boolean fps;
    private BufferedImage image;
    public static Random rand;
    
    public Configura conf;
    
    public static List<Object> objects;
    public static Ball ball;
    public static Robot robot;
    public int[] pixels;
    
	public static String mode = "Stop";
	
	public Simulator() {
    	rand = new Random();
    	objects = new ArrayList<Object>();
    	
    	addKeyListener(this);
    	addMouseListener(this);
		setPreferredSize(new Dimension(WIDTH,HEIGHT));
	    initFrame();
	    
	    conf = new Configura();
	    initConf();
	    
	    image = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
		pixels = ((DataBufferInt)image.getRaster().getDataBuffer()).getData();
	    
	    ball = new Ball(X(0),Y(0),42,Color.red);
	    objects.add(ball);
    }

	public void initFrame() {
		frame = new JFrame ("Simulator - Soccer");
		frame.add(this);
		frame.setResizable(false);
		frame.pack();
		frame.setLocationRelativeTo(null);
		frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		frame.setVisible(true);
	}
	
	public void initConf() {
		conf.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
	    conf.setSize(350,650);
	    conf.setResizable(false);
	    conf.setVisible(true);
	}
    
    public synchronized void start(){
    	thread = new Thread(this);
    	isRunning = true;
    	thread.start();
    }
    
    public synchronized void stop(){
    	isRunning = false;
    	try {
			thread.join();
		} catch (InterruptedException e) {
			e.printStackTrace();
		}
    }
    
	public static void main(String args[]) {
		Simulator sim = new Simulator();
		sim.start();
	}
	
	public void tick(){
		for(int i = 0; i < objects.size(); i++) {
			Object e = objects.get(i);
			e.tick();
		}
	}
	
	public static void resetAll() {
		if(mode == "Start") {
			for(int i = 0; i < objects.size(); i++) {
				Object e = objects.get(i);
				e.resetPosition();
			}
		}
	} 
	
	public static int X(int cm) {
		return 607+(cm*5); 
	}
	
	public static int Y(int cm) {
		return 455+(cm*5); 
	}
	
	public void render() {
		BufferStrategy bs = this.getBufferStrategy();
		if (bs == null) {
			this.createBufferStrategy(3);
			return;
		}

		Graphics g = image.getGraphics();
		g.setColor(new Color(0, 0, 0));
		g.fillRect(0, 0, WIDTH, HEIGHT);
		
		//CAMPO
		g.setColor(new Color(0, 255, 0)); //1215 910
		g.fillRect(0, 0, 1095+120, 790+120);
		
		//LINHAS
		g.setColor(new Color(255, 255, 255));
		g.fillRect(225-165, 37-5+23, 1095, 5);
		g.fillRect(225-165, 37+790+23, 1095, 5);
		g.fillRect(225-5-165, 37-5+23, 5, 790+10);
		g.fillRect(225+1095-165, 37-5+23, 5, 790+10);

		g.fillRect(225+125-165, 37+270+23, 5, 250);
		g.fillRect(225+1095-125-165, 37+270+23, 5, 250);
		
		g.fillRect(225-165, 232+23, 50, 5);
		g.fillRect(225-165, 232+400+23, 50, 5);
		g.fillRect(225+1095-50-165, 232+23, 50, 5);
		g.fillRect(225+1095-50-165, 232+400+23, 50, 5);
		
		g.fillArc(330-75-165-60, 37+270-75+23-1, 160, 160, 0, 90);
		g.fillArc(330-75-165-60, 37+270-75+23+245, 160, 160, 0, -90);
		g.fillArc(330-75-165-60+1000, 37+270-75+23-1, 160, 160, 90, 90);
		g.fillArc(330-75-165-60+1000, 37+270-75+23+245, 160, 160, -90, -90);
		
		g.setColor(new Color(0, 255, 0));
		g.fillArc(330-75-165-60-5, 37+270-75+23-1+5, 160, 160, 0, 90);
		g.fillArc(330-75-165-60-5, 37+270-75+23+245-5, 160, 160, 0, -90);
		g.fillArc(330-75-165-60+1000+5, 37+270-75+23-1+5, 160, 160, 90, 90);
		g.fillArc(330-75-165-60+1000+5, 37+270-75+23+245-5, 160, 160, -90, -90);
		
		//GOLS	
		g.setColor(new Color(255, 255, 0));
		g.fillRect(175-165, 282+23, 50, 300);
		g.setColor(new Color(0, 0, 255));
		g.fillRect(225+1095-165, 282+23, 50, 300);
		
		//MARCAS
		g.setColor(new Color(0, 0, 0));
		g.drawOval(622-165, 282+23, 300, 300);
		g.fillOval(764+4-165, 424+4+23, 8, 8);
		g.fillOval(225+225-165, 37+225+23, 8, 8);
		g.fillOval(225+225-165, 37+790-225+23, 8, 8);
		g.fillOval(225+1095-225-165, 37+225+23, 8, 8);
		g.fillOval(225+1095-225-165, 37+790-225+23, 8, 8);
		
		if(mode == "Start") {
			for(int i = 0; i < objects.size(); i++) {
				Object e = objects.get(i);
				e.render(g);
			}
		}

		g.dispose();
		g = bs.getDrawGraphics();
		g.drawImage(image, 0, 0, WIDTH, HEIGHT, null);

		bs.show();
	}

	public void run() {
		long lastTime = System.nanoTime();
		double amountOfTicks = 60.0;
		double ns = 1000000000 / amountOfTicks;
		double delta = 0;
		FPS = 0;
		double timer = System.currentTimeMillis();
		requestFocus();
		while(isRunning){
			long now = System.nanoTime();
			delta+= (now - lastTime) / ns;
			lastTime = now;	
			if(delta >= 1) {
				tick();
				render();
				FPS++;
				delta--;
			}
			if(System.currentTimeMillis() - timer >= 1000) {
				System.out.println("FPS: "+ FPS);
				fps = true;
				FPS = 0;
				timer+=1000;
			}
		}
	}

	public void keyPressed(KeyEvent e) {

	}


	public void keyReleased(KeyEvent e) {
		
	}

	
	public void keyTyped(KeyEvent arg0) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void mouseClicked(MouseEvent arg0) {
		
	}

	@Override
	public void mouseEntered(MouseEvent arg0) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void mouseExited(MouseEvent arg0) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void mousePressed(MouseEvent arg0) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void mouseReleased(MouseEvent arg0) {
		// TODO Auto-generated method stub
		
	}
}
