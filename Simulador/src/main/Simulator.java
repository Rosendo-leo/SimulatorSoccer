package main;

import java.awt.Canvas;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Graphics;
import java.awt.Toolkit;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.image.BufferStrategy;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPasswordField;
import javax.swing.JTextField;

public class Simulator extends Canvas implements Runnable, KeyListener, MouseListener{
		
	private static final long serialVersionUID = 1L;
	public static JFrame frame;
	public static JFrame control;
	private Thread thread;
	private boolean isRunning = true;
	public static final int WIDTH = 1544;
	public static final int HEIGHT = 864;
    public static int FPS;
    public static boolean fps;
    private BufferedImage image;
    public static Random rand;
    
    public static List<Object> objects;
    public int[] pixels;
    
	public static String mode = "Choose";
	
	public Simulator() {
    	rand = new Random();
    	addKeyListener(this);
    	addMouseListener(this);
		setPreferredSize(new Dimension(WIDTH,HEIGHT));
	    initFrame();
	    
	    image = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
		pixels = ((DataBufferInt)image.getRaster().getDataBuffer()).getData();
	    objects = new ArrayList<Object>();
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
			//e.tick();
		}
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

		for(int i = 0; i < objects.size(); i++) {
			Object e = objects.get(i);
			//e.tick();
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
